import { z } from "zod";

export const sourceSchema = z.object({
  name: z.string().min(1, "Name is required"),
  url: z.string().url("Invalid URL").startsWith("http", "URL must start with http"),
  category: z.enum(["Tech", "Business", "News", "Entertainment", "Science", "Health", "Sport"]).optional().nullable(),
});

export const scheduleSchema = z.object({
  name: z.string().min(1, "Schedule name is required"),
  cron_expression: z.string().min(1, "Cron expression is required"),
  timezone: z.string(),
  max_articles: z.number().int().min(1).max(50),
  profile: z.string().min(1, "Profile is required"),
  language: z.string().min(1),
});

export const deliveryChannelSchema = z.object({
  type: z.enum(["discord", "email"]),
  webhook_url: z.string().optional(),
  email: z.string().email().optional(),
});

export type SourceFormData = z.infer<typeof sourceSchema>;
export type ScheduleFormData = z.infer<typeof scheduleSchema>;
export type DeliveryChannelData = z.infer<typeof deliveryChannelSchema>;
