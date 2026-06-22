// Supabase Edge Function: process-receipt
//
// Receives a receipt image/PDF reference, runs it through an AI vision model,
// and returns a strongly typed extraction matching the client's
// `extractedReceiptSchema`. The AI provider key lives in function secrets and
// is never shipped to the client.
//
// Deploy: supabase functions deploy process-receipt
// Secrets: supabase secrets set OPENAI_API_KEY=sk-...
//
// deno-lint-ignore-file no-explicit-any
import { serve } from 'https://deno.land/std@0.224.0/http/server.ts';

interface RequestBody {
  uri: string;
  mimeType: string;
}

interface ExtractedReceipt {
  retailer: string | null;
  purchase_date: string | null;
  items: { name: string; price: number | null }[];
  total_amount: number | null;
  warranty_months: number | null;
  warranty_text: string | null;
  confidence: number;
}

const SYSTEM_PROMPT = `You are a receipt parser. Extract structured data from the
receipt image and respond ONLY with minified JSON matching:
{"retailer":string|null,"purchase_date":"YYYY-MM-DD"|null,
"items":[{"name":string,"price":number|null}],"total_amount":number|null,
"warranty_months":number|null,"warranty_text":string|null,"confidence":number}`;

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { uri } = (await req.json()) as RequestBody;
    if (!uri) {
      return json({ error: 'Missing "uri"' }, 400);
    }

    const apiKey = Deno.env.get('OPENAI_API_KEY');
    if (!apiKey) {
      // No key configured — return a safe empty extraction so the client can
      // fall back to manual entry rather than crash.
      return json(emptyExtraction());
    }

    const aiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          {
            role: 'user',
            content: [
              { type: 'text', text: 'Extract this receipt.' },
              { type: 'image_url', image_url: { url: uri } },
            ],
          },
        ],
      }),
    });

    if (!aiResponse.ok) {
      return json({ error: `AI provider error: ${aiResponse.status}` }, 502);
    }

    const payload = await aiResponse.json();
    const content = payload?.choices?.[0]?.message?.content ?? '{}';
    const parsed = normalize(JSON.parse(content));
    return json(parsed);
  } catch (e) {
    return json({ error: (e as Error).message }, 500);
  }
});

function normalize(raw: any): ExtractedReceipt {
  return {
    retailer: raw.retailer ?? null,
    purchase_date: raw.purchase_date ?? null,
    items: Array.isArray(raw.items)
      ? raw.items.map((i: any) => ({ name: String(i.name ?? ''), price: numOrNull(i.price) }))
      : [],
    total_amount: numOrNull(raw.total_amount),
    warranty_months: raw.warranty_months != null ? Math.trunc(Number(raw.warranty_months)) : null,
    warranty_text: raw.warranty_text ?? null,
    confidence: typeof raw.confidence === 'number' ? raw.confidence : 0.5,
  };
}

function emptyExtraction(): ExtractedReceipt {
  return {
    retailer: null,
    purchase_date: null,
    items: [],
    total_amount: null,
    warranty_months: null,
    warranty_text: null,
    confidence: 0,
  };
}

function numOrNull(v: unknown): number | null {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}
