// Top FAQs collected from real user data, organized by category
// These are shown as starter chips before birth details are collected

export interface FaqCategory {
  label: string;
  emoji: string;
  color: string;         // Tailwind border + text color
  bgColor: string;       // Tailwind background color
  questions: string[];   // Top questions in this category
}

export const FAQ_CATEGORIES: FaqCategory[] = [
  {
    label: "Marriage",
    emoji: "💍",
    color: "border-pink-300 text-pink-800",
    bgColor: "bg-pink-50 hover:bg-pink-100 hover:border-pink-400",
    questions: [
      "💍 When will I get married?",
      "💍 Will it be a love marriage or an arranged marriage?",
      "💍 When will my marriage be finalized?",
      "💍 What kind of life partner will I get?",
      "💍 When are my marriage chances?",
      "💍 Will I get married this year?",
    ]
  },
  {
    label: "Love & Ex",
    emoji: "💑",
    color: "border-rose-300 text-rose-800",
    bgColor: "bg-rose-50 hover:bg-rose-100 hover:border-rose-400",
    questions: [
      "💑 Will my ex come back to me?",
      "💑 Is he loyal to me?",
      "💑 Will he realize he still loves me?",
      "💑 Is there someone else in his life?",
      "💑 What is on his mind?",
      "💑 Will I have a love marriage?",
    ]
  },
  {
    label: "Career & Job",
    emoji: "💼",
    color: "border-blue-300 text-blue-800",
    bgColor: "bg-blue-50 hover:bg-blue-100 hover:border-blue-400",
    questions: [
      "💼 When will I get a job?",
      "💼 Will I get a government job?",
      "💼 When will I get a promotion?",
      "💼 Which field should I go into?",
      "💼 Will I be selected this year?",
      "💼 What about my career?",
    ]
  },
  {
    label: "Finance",
    emoji: "💰",
    color: "border-green-300 text-green-800",
    bgColor: "bg-green-50 hover:bg-green-100 hover:border-green-400",
    questions: [
      "💰 How will my financial life be?",
      "💰 When will my debt be cleared?",
      "💰 Will I succeed in business?",
      "💰 How will my wealth be in the future?",
      "💰 Is this a good time to invest?",
    ]
  },
  {
    label: "Abroad",
    emoji: "🌍",
    color: "border-indigo-300 text-indigo-800",
    bgColor: "bg-indigo-50 hover:bg-indigo-100 hover:border-indigo-400",
    questions: [
      "🌍 Will I go abroad?",
      "🌍 When will I get a chance to go abroad?",
      "🌍 Will I settle in a foreign country?",
      "🌍 In which field will I get a job abroad?",
    ]
  },
  {
    label: "Health",
    emoji: "🏥",
    color: "border-orange-300 text-orange-800",
    bgColor: "bg-orange-50 hover:bg-orange-100 hover:border-orange-400",
    questions: [
      "🏥 Why am I facing health issues?",
      "🏥 How will my health be in the future?",
      "🏥 Tell me about my health and marriage.",
      "🏥 What remedies should I follow for good health?",
    ]
  },
  {
    label: "Remedies",
    emoji: "🪬",
    color: "border-purple-300 text-purple-800",
    bgColor: "bg-purple-50 hover:bg-purple-100 hover:border-purple-400",
    questions: [
      "🪬 What remedies should I do?",
      "🪬 Which gemstone should I wear?",
      "🪬 What mantra should I chant?",
      "🪬 Which color is lucky for me?",
      "🪬 What fasting should I do?",
    ]
  },
  {
    label: "Family",
    emoji: "👨‍👩‍👧",
    color: "border-yellow-400 text-yellow-900",
    bgColor: "bg-yellow-50 hover:bg-yellow-100 hover:border-yellow-400",
    questions: [
      "👨‍👩‍👧 When will I have children?",
      "👨‍👩‍👧 How will my married life be?",
      "👨‍👩‍👧 What is my brother's future?",
      "👨‍👩‍👧 Will my family agree to my relationship?",
    ]
  },
];
