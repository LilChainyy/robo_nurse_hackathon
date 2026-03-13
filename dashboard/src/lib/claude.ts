import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function generateDoctorNote(
  clinicalSummary: string,
  relayTranscript: Array<{ speaker: string; textOriginal: string; textTranslated: string }>,
  patientName: string,
  patientLanguage: string
): Promise<{
  diagnosis: string;
  prescribedMedications: string[];
  instructions: string;
  followUp: string;
  fullNoteText: string;
}> {
  const transcriptText =
    relayTranscript.length > 0
      ? relayTranscript
          .map(
            (m) =>
              `[${m.speaker.toUpperCase()}] ${m.textTranslated || m.textOriginal}`
          )
          .join("\n")
      : "No doctor-patient consultation transcript available yet.";

  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    max_tokens: 1000,
    messages: [
      {
        role: "system",
        content: "You are a medical AI assistant helping generate structured doctor notes. Always respond with valid JSON only, no markdown.",
      },
      {
        role: "user",
        content: `Based on the following patient intake data and doctor-patient consultation transcript, generate a structured doctor note.

PATIENT: ${patientName} (Language: ${patientLanguage})

INTAKE SUMMARY:
${clinicalSummary}

CONSULTATION TRANSCRIPT:
${transcriptText}

Generate the note in this exact JSON format (no markdown, just raw JSON):
{
  "diagnosis": "Primary diagnosis based on symptoms and consultation",
  "prescribedMedications": ["Medication 1 with dosage", "Medication 2 with dosage"],
  "instructions": "Patient care instructions",
  "followUp": "Follow-up recommendations",
  "fullNoteText": "The complete formatted doctor note as plain text"
}

Be professional and concise. Use clinical language appropriate for a medical record.`,
      },
    ],
  });

  const text = response.choices[0]?.message?.content || "";

  try {
    // Strip markdown code fences if present
    const cleaned = text.replace(/```json\s*\n?/g, "").replace(/```\s*$/g, "").trim();
    return JSON.parse(cleaned);
  } catch {
    return {
      diagnosis: "",
      prescribedMedications: [],
      instructions: "",
      followUp: "",
      fullNoteText: text,
    };
  }
}
