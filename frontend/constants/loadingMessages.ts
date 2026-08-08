export type LoadingMessageType = "fact" | "tip" | "status";

export interface LoadingMessage {
  type: LoadingMessageType;
  title: string;
  message: string;
}

export const loadingMessages: LoadingMessage[] = [
  {
    type: "fact",
    title: "Did you know?",
    message:
      "The same grocery cart can cost over ₹250 more depending on the platform and time of day.",
  },
  {
    type: "fact",
    title: "Did you know?",
    message:
      "Delivery charges often make a 'cheaper' cart more expensive than expected.",
  },
  {
    type: "fact",
    title: "Did you know?",
    message:
      "Many shoppers compare only product prices and forget platform fees.",
  },
  {
    type: "tip",
    title: "Savings Tip",
    message:
      "Adding one more item can sometimes unlock free delivery and reduce your final bill.",
  },
  {
    type: "tip",
    title: "Savings Tip",
    message:
      "Platform memberships are only useful if they actually reduce your total order cost.",
  },
  {
    type: "tip",
    title: "Savings Tip",
    message:
      "Buying every item from a single app isn't always the cheapest option.",
  },
  {
    type: "status",
    title: "Optimizing",
    message:
      "Comparing prices across supported grocery platforms...",
  },
  {
    type: "status",
    title: "Optimizing",
    message:
      "Calculating the cheapest combination for your cart...",
  },
  {
    type: "status",
    title: "Optimizing",
    message:
      "Applying memberships, offers and delivery charges...",
  },
];