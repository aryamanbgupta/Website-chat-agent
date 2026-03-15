export const STARTER_PROMPTS = [
  {
    label: "Ice maker not working",
    message: "The ice maker on my Whirlpool fridge is not working",
    icon: "snowflake" as const,
  },
  {
    label: "Find a specific part",
    message: "Find part PS11752778",
    icon: "search" as const,
  },
  {
    label: "Check part compatibility",
    message: "Is PS10065979 compatible with model WDT780SAEM1?",
    icon: "check-circle" as const,
  },
  {
    label: "Dishwasher won't drain",
    message: "My dishwasher won't drain",
    icon: "droplets" as const,
  },
];

export const API_PATHS = {
  chat: "/api/chat",
  health: "/api/health",
} as const;
