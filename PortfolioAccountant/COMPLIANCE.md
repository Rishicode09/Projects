# Legal and professional boundaries

This document exists because "make my tax efficient" and "help me pay less tax"
are the same sentence in ordinary speech, and describe two completely different
things in law. Most people asking have no intention of doing anything wrong.
The distinction matters anyway, because the consequences differ enormously and
the line is not where intuition puts it.

## Evasion, avoidance, planning

### Tax evasion — criminal

Misrepresenting reality to HMRC. Concealing income. Inventing or inflating
expenses. Backdating or altering documents. Hiding who really owns an asset.
Understating a disposal. Paying cash to keep something off the books.

This is a criminal offence. It carries unlimited fines and imprisonment, and
liability is personal — a company structure does not absorb it. There is no
version of this the package or the agent will assist with, however it is
framed, and regardless of amount.

**If it has already happened**, the response is disclosure, not concealment and
not quiet correction. See below.

### Avoidance schemes — legal, and usually a bad idea

Contrived arrangements designed to produce a tax result Parliament did not
intend. Not criminal. Also not safe:

- The **General Anti-Abuse Rule** (Finance Act 2013 Part 5) counteracts abusive
  arrangements outright.
- The **Ramsay principle** lets courts look at the composite effect of a series
  of steps rather than each step in isolation, which is what most schemes rely
  on.
- **DOTAS** requires notifiable arrangements to be disclosed, and using one
  means declaring the scheme reference on your return.
- **Accelerated payment notices** can require the tax to be paid up front,
  before any dispute is resolved.
- Promoters take their fee at the outset. The interest and penalties arrive
  years later, and they arrive at the user.

The package does not design these. Not because they are illegal — because they
are bad advice, and because someone selling a structure is not the same as
someone advising on one.

### Tax planning — legal, sensible, and the actual work

Choosing between genuinely available alternatives and taking the reliefs
Parliament legislated for, on the terms it set:

- Contributing to a pension, particularly in the 60% band between £100,000 and
  £125,140 where the personal allowance tapers.
- Holding an asset jointly with a spouse who genuinely owns their share, with a
  declaration of trust and Form 17 where the split is unequal.
- Timing a disposal that is going to happen anyway across 5 April, using two
  annual exempt amounts instead of one.
- Claiming capital allowances, replacement of domestic items relief, or the
  property allowance where you qualify.
- Choosing a company structure for a new acquisition, with the full costs
  counted rather than just the headline rate.

Every planning point the package raises states its statutory basis, the
conditions that must genuinely be met, and what happens if they are not.

### The test

**Would this still make sense if HMRC read the entire file?**

If a step only works because nobody looks at the whole picture, it is not
planning. Contemporaneous evidence of commercial purpose is what distinguishes
ordinary planning from an arrangement, and it cannot be created afterwards.

## What the agent will not do

1. Conceal or under-declare income of any kind.
2. Create, backdate or alter an invoice, contract or receipt.
3. Record personal expenditure as business expenditure.
4. Hide beneficial ownership of an asset or income stream.
5. Disguise employment as self-employment to reduce NIC.
6. Move money to obscure its source or defeat a creditor.
7. Design a contrived scheme whose main purpose is a tax advantage.
8. Advise on avoiding detection by HMRC or an auditor.
9. File, submit or sign a return, or approve accounts as though a person had
   reviewed them.
10. Present an estimate as a filed or agreed figure.

`python3 -m portfolio_accountant.cli refusals` prints this list.

## What it cannot do, regardless of instruction

These are regulated acts. Doing them requires a qualified person with
professional indemnity insurance and personal accountability:

- **Filing** returns with HMRC or Companies House.
- **Signing off** statutory accounts. Directors approve accounts and are
  personally liable for them.
- **Audit opinions.** A statutory audit is performed by a registered auditor.
  This package produces a *review file*, which is a different and lesser thing,
  and labels it that way.
- **Regulated tax advice** where the outcome turns on residence, domicile,
  family circumstances or intentions the engine cannot see.
- **Expert evidence.** Forensic output here directs enquiry. Evidence for legal
  proceedings must be prepared by an expert who can be cross-examined on it.

## If something is already wrong

Discovering a past error is common and usually not sinister. The response is
what matters, and quietly fixing it forward is the wrong one.

- **Undeclared rental income** — HMRC's Let Property Campaign exists precisely
  for this, with materially lower penalties than discovery.
- **Other under-declaration** — the Digital Disclosure Service. In serious
  cases the Contractual Disclosure Facility (Code of Practice 9) offers
  protection from criminal prosecution in exchange for full disclosure.
- **VAT errors** — correctable on the next return below the threshold, form
  VAT652 above it. Deliberately splitting a large error across returns to stay
  below the threshold is itself an offence.
- **Filed accounts** — voluntary amendment before anyone asks is treated far
  better than correction extracted later.

**Unprompted disclosure attracts substantially lower penalties than a
disclosure made after HMRC opens an enquiry.** Take specialist advice on the
route before making one; the route chosen has real consequences.

## Money laundering

Regulated professionals — accountants, auditors, solicitors — have obligations
under the Proceeds of Crime Act 2002 and the Money Laundering Regulations,
including submitting Suspicious Activity Reports and the offence of tipping off
a suspect. Those obligations sit with the professional, not with software.

If a forensic review surfaces something suggesting proceeds of crime, that is a
point to take advice on immediately and privately. It is not something to raise
with the person concerned, and not something to handle informally.

## Data protection

These records contain personal data about tenants, employees and family
members. Under UK GDPR: keep only what is needed, keep it secure, and keep it
no longer than the retention period requires. Tenant records are the most
sensitive holding in a typical portfolio and the least often thought about.

Retention periods, and why the usual answer is wrong for property, are in the
`record_keeping` section of the jurisdiction config. A 1998 extension invoice
is what proves the CGT base cost in 2035; the standard six years is no help at
all there.

## Standing position

Every substantive output states what it is and is not, and ends by naming what
a qualified human must do before anything is filed. That is not a disclaimer to
be skimmed past. It is the next action.
