// A pack as GET /api/teaching/packs/<id>/ returns it (lesson-plan edits already merged), for tests.
const question = (id, prompt, difficulty, extra = {}) => ({
  id,
  type: "mcq",
  prompt,
  choices: [
    { id: id * 10 + 1, text: "distance / time", is_correct: true },
    { id: id * 10 + 2, text: "distance x time", is_correct: false },
  ],
  numeric_answer: null,
  accepted_answers: [],
  explanation: `Explanation for ${prompt}`,
  marking_guide: "",
  marks: 1,
  difficulty,
  ...extra,
});

export const packFixture = {
  id: 5,
  classroom: 3,
  unit_id: 7,
  lesson_id: 31,
  created_at: "2026-10-20T09:00:00+02:00",
  language: "en",
  ai_used: true,
  students_needing_help: [{ id: 11, display_name: "Aline M.", average: 30, answered: 4 }],
  assignments: [],
  document: {
    version: 1,
    language: "en",
    classroom: { id: 3, name: "S2 B Physics", grade: "S2", size: 42 },
    unit: { id: 7, label: "S2 Unit 3: Motion", number: 3, title: "Motion", key_unit_competence: "Describe motion." },
    lesson: { id: 31, slug: "speed", title: "Speed and velocity" },
    insight: {
      data_enough: true,
      average: 41.5,
      other_units: [{ label: "S2 Unit 2: Forces", average: 63 }],
      misconceptions: [
        {
          question_id: 120,
          prompt: "How do you work out speed?",
          wrong_choice: "distance x time",
          share: 0.62,
          answered: 37,
          correct: "distance / time",
          explanation: "Divide the distance by the time.",
        },
      ],
      hardest: [{ question_id: 121, prompt: "What is the unit of speed?", correct_share: 0.18, answered: 35 }],
    },
    plan: {
      school: "Lycée de Kigali",
      teacher: "Jean Habimana",
      term: "",
      date: "2026-10-20",
      subject: "Physics",
      class_name: "S2 B Physics",
      lesson_number: "2",
      duration: "40",
      class_size: "42",
      sen_learners: "",
      unit_number: "3",
      unit_title: "Motion",
      key_unit_competence: "Describe motion.",
      lesson_title: "Speed and velocity",
      objective: "By the end of this lesson, learners can explain and use Speed and velocity.",
      location: "In the classroom",
      materials: "The Iga worksheet, the board, and the student's book.",
      references: "REB Physics S2",
      steps: [
        { name: "introduction", minutes: 5, teacher: "Ask who ran fastest.", learners: "Vote.", competences: "Critical thinking" },
        { name: "development", minutes: 25, teacher: "Activity 1: Speed.", learners: "Work in pairs.", competences: "Problem solving" },
        { name: "conclusion", minutes: 10, teacher: "Summarise.", learners: "Answer.", competences: "Lifelong learning" },
      ],
      evaluation: "1. How do you work out speed?",
      self_evaluation: "",
    },
    polish: { hook: "Ask who ran fastest.", simpler: "Speed is how far you go each second.", ai: true },
    worksheet: {
      support: [question(201, "Easy speed question", 1)],
      core: [question(120, "How do you work out speed?", 2)],
      stretch: [],
      notes: ["No stretch questions exist for this unit yet."],
    },
    quiz: { diagnostic: false, questions: [question(120, "How do you work out speed?", 2)] },
    notes: [],
    generated_at: "2026-10-20T09:00:00+02:00",
  },
};

/** A copy of the fixture with changes deep-merged into its document. */
export function packWith({ document = {}, ...rest } = {}) {
  const base = structuredClone(packFixture);
  return {
    ...base,
    ...rest,
    document: {
      ...base.document,
      ...document,
      insight: { ...base.document.insight, ...(document.insight || {}) },
      polish: { ...base.document.polish, ...(document.polish || {}) },
      quiz: { ...base.document.quiz, ...(document.quiz || {}) },
    },
  };
}
