// Tap-to-learn: short, plain-English definitions for terms beginners can't avoid on Tremor.
// Keep each one to 1-3 short sentences a college freshman could repeat to a friend. No statistics here.

export type GlossaryEntry = { term: string; text: string; group: "trials" | "fda" | "stocks" | "tremor" };

export const GLOSSARY = {
  clinical_trial: {
    term: "Clinical trial",
    group: "trials",
    text: "A research study that tests a treatment in people. Drugs go through several trials, called phases, before they can be sold.",
  },
  phase1: {
    term: "Phase 1",
    group: "trials",
    text: "The first test of a drug in people, usually a small group. The main question is whether it's safe and what dose to use.",
  },
  phase2: {
    term: "Phase 2",
    group: "trials",
    text: "A medium-sized test to see whether the drug seems to work, and to keep checking safety. Good results can lead to a bigger Phase 3 trial.",
  },
  phase3: {
    term: "Phase 3",
    group: "trials",
    text: "The big final test before a company asks the FDA for approval. It usually compares the drug with today's standard treatment in many patients. Results often move the stock a lot.",
  },
  primary_outcome: {
    term: "Main goal (primary outcome)",
    group: "trials",
    text: "The one main thing a trial is designed to measure, chosen in advance, like how long patients live without the cancer growing. Whether the trial \"worked\" is judged mostly on this.",
  },
  enrollment: {
    term: "Enrollment",
    group: "trials",
    text: "How many patients the trial signs up. While signing up is open, the record shows a planned number; afterward it shows the final count.",
  },
  drug_target: {
    term: "Drug target",
    group: "trials",
    text: "The specific thing in the body a drug is built to attach to or block, like a protein called PD-1. Drugs aimed at the same target often succeed or fail for similar reasons, so one drug's failure can worry investors in its rivals.",
  },
  stopped: {
    term: "Stopped early",
    group: "trials",
    text: "A trial can be suspended (paused), terminated (ended early), or withdrawn (ended before any patient joined). Companies give a reason, which can be about the drug or just a business decision.",
  },
  oncology: {
    term: "Oncology",
    group: "trials",
    text: "The branch of medicine that treats cancer.",
  },
  fda: {
    term: "FDA",
    group: "fda",
    text: "The US Food and Drug Administration, the government agency that decides whether a new drug can be sold in the US.",
  },
  pdufa: {
    term: "PDUFA date",
    group: "fda",
    text: "The FDA's deadline to decide on a drug, named after a law (the Prescription Drug User Fee Act). The FDA can decide early or extend the deadline.",
  },
  approved_medicine: {
    term: "FDA-approved medicine",
    group: "fda",
    text: "A drug the FDA has allowed to be sold in the US after it passed its trials. Sales of approved medicines bring in money, so a company that has some depends less on any one trial.",
  },
  fda_advisory: {
    term: "FDA advisory meeting",
    group: "fda",
    text: "A public meeting where outside experts discuss a drug and vote on advice for the FDA. The FDA usually, but not always, follows the vote.",
  },
  stock: {
    term: "Stock (share)",
    group: "stocks",
    text: "A small piece of ownership in a company. Its price goes up and down with what buyers and sellers think the company will be worth.",
  },
  ticker: {
    term: "Ticker",
    group: "stocks",
    text: "The short code a company's stock trades under, like MRK for Merck.",
  },
  sec: {
    term: "SEC filing",
    group: "stocks",
    text: "A report a public company must send to the SEC, the US agency that oversees the stock market. Anyone can read these for free.",
  },
  form_8k: {
    term: "8-K",
    group: "stocks",
    text: "A short SEC report companies must file within a few business days of important news, like an executive leaving, layoffs, or big trial results.",
  },
  insider: {
    term: "Insider",
    group: "stocks",
    text: "Someone who runs the company or owns a big part of it, like executives, board members, and large shareholders. They must report when they buy or sell its shares.",
  },
  plan_10b5_1: {
    term: "Pre-planned sale (10b5-1 plan)",
    group: "stocks",
    text: "A legal plan that sells an insider's shares on a schedule set months ahead. Because it was decided earlier, it says less about what the insider thinks today.",
  },
  runway: {
    term: "Money left (cash runway)",
    group: "stocks",
    text: "How many months a company could keep going at its recent spending rate with the cash it has now, before it needs more money.",
  },
  dilution: {
    term: "Selling new shares (dilution)",
    group: "stocks",
    text: "When a company creates and sells new shares to raise cash, each existing share owns a smaller slice of the company, which usually pushes its price down.",
  },
  layoff_notice: {
    term: "Layoff notice (WARN)",
    group: "stocks",
    text: "Many states require companies to file a public notice before large layoffs. It's called a WARN notice, after the law that requires it.",
  },
  worry_score: {
    term: "Worry score",
    group: "tremor",
    text: "Tremor's 0-100 count of warning signs for a trial: green (Calm), yellow (Shaky), red (Tremor). Higher means more warning signs. It is not a prediction.",
  },
  tremor_alert: {
    term: "Tremor (alert)",
    group: "tremor",
    text: "Anything that could give you a head start before big news: a major change to a trial's record, a key executive leaving, a stopped trial, or a big score jump.",
  },
} satisfies Record<string, GlossaryEntry>;

export type GlossaryId = keyof typeof GLOSSARY;
