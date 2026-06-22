import { z } from 'zod';

export const emailSchema = z.string().email('Enter a valid email address');

export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Za-z]/, 'Include at least one letter')
  .regex(/[0-9]/, 'Include at least one number');

export const signInSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
});

export const signUpSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
});

export const resetPasswordSchema = z.object({
  email: emailSchema,
});

export type SignInInput = z.infer<typeof signInSchema>;
export type SignUpInput = z.infer<typeof signUpSchema>;
