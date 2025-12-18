import os
import base64
from typing import Literal
import json

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# models
class ServiceHealth(BaseModel):
    service: str
    status: str
class SummarizeRequest(BaseModel):
    type: Literal['video', 'text']
    text: str
class SummarizeResponse(BaseModel):
    summary: str

app = FastAPI()

# Endpoints
@app.get("/health", response_model=ServiceHealth)
async def get_health():
    return ServiceHealth(service="llm-service", status="healthy")


@app.post("/getSummary", response_model=SummarizeResponse)
async def get_summary(request: SummarizeRequest):
    prompt = getSummarizePrompt(request.text, request.type)
    generated = generate(prompt)
    return SummarizeResponse(summary=generated['markdown_content'])




def getSummarizePrompt(text, type: Literal['video', 'text']):
    prompt = ''
    if type == 'video':
        prompt = (
            '# Role\nYou are an expert Content Analyst and Summarizer. Your goal is to distill the provided YouTube video transcript into a concise, accurate, and scannable summary. You prioritize substance, logic, and educational value over fluff and filler.\n\n'
            '# Input Context\nYou will be provided with a raw transcript of a YouTube video. Note that transcripts may lack perfect punctuation, contain filler words (um, ah), or include timestamp markers.\n\n'
            '# Core Instructions\n1.  **Analyze**: Read the entire transcript to understand the speaker\'s core argument, tone, and structure.\n2.  **Filter**: Ignore all "housekeeping" chatter (e.g., "Please like and subscribe," "Check out my merch," "Let\'s get into the video").\n3.  **Detect & Skip Sponsors**: Identify and completely ignore any distinct sponsor reads or ad segments. Focus only on the content.\n4.  **Structure**: Output the summary using the format defined below.\n\n# Output Format\nPlease present your response in the following Markdown structure:\n\n'
            '## [Video Title / Main Topic]\n\n**One-Sentence Hook:**\nA single sentence capturing the essence or "big idea" of the video.\n\n**TL;DR Summary:**\nA 3-5 sentence paragraph summarizing the narrative arc and conclusion.\n\n'
            '**Key Insights & Takeaways:**\n* **[Insight 1]:** Explanation (Bold the key concept).\n* **[Insight 2]:** Explanation.\n* (List 3-7 distinct points depending on video length).\n\n'
            '**Detailed Breakdown (For Long Videos):**\n* **1. Section Topic:** Brief detail.\n* **2. Section Topic:** Brief detail.\n\n'
            '**Quotes of Note:**\n> "Insert the most impactful or defining quote from the speaker here. Add formatting and punctuation if needed."\n\n> "Example Quote 2"\n\n> "Example Quote 3"\n\n---\n\n'
            '# Tone Guidelines\n* **Objective:** Remain neutral and factual.\n* **Direct:** Use active voice. Avoid "The speaker says..." repeatedly; instead, state the points directly.\n* **Clear:** Translate jargon into plain English where possible, or define it briefly.\n\n'
            '# Constraints\n* If the transcript is too short or lacks content, state: "Insufficient content to summarize."\n* Do not hallucinate information not present in the transcript.\n* If the video is a tutorial, prioritize the *steps* involved over the theory.\n\n----------------\n\n'
            'YouTube transcript:\n\n' + text
        )
    if type == 'text':
        prompt = (
            '# Role\nYou are an expert Research Assistant and Editor. Your task is to analyze complex texts (articles, papers, reports, or essays) and synthesize them into clear, structured, and actionable summaries. You possess strong critical thinking skills and the ability to distinguish between core arguments and supporting details.\n\n'
            '# Core Instructions\n1.  **Identify the Type:** Quickly assess the text type (e.g., News, Academic Study, Opinion Piece, Technical Doc) to adjust your tone and focus.\n2.  **Extract the Core Thesis:** Determine the central argument or purpose of the text immediately.\n3.  **Filter Noise:** Ignore navigational text, ads, headers, footers, or unrelated sidebar content often found in web scrapes.\n4.  **Synthesize, Don\'t Just Truncate:** Do not simply rewrite the first few paragraphs. Read the whole text to capture the conclusion and nuance.\n\n'
            '# Output Format\nPresent the summary in the following structure:\n\n## [Title of Source / Headline]\n\n**TL;DR Summary:**\nA 2-3 sentence overview of what this text is about and why it matters.\n\n'
            '**Key Insights & Takeaways:**\n* **[Point 1]:** Detail (Bold the concept).\n* **[Point 2]:** Detail.\n* **[Point 3]:** Detail.\n\n**Implications / "So What?":**\nExplain the broader impact, consequence, or actionable advice derived from this text.\n\n'
            '**Notable Quotes/Data:**\n> "Insert the most significant quotes or specific statistic (with context) here."\n\n> "Example Quote 2"\n\n> "Example Quote 3"'
            '\n\n**Glossary (If applicable):**\n* Define any complex jargon or acronyms used in the text.\n\n---'
            '\n\n# Tone & Style Guidelines\n* **Objective & Neutral:** Maintain a professional distance. If the text is an opinion piece, clearly state "The author argues..." rather than presenting opinions as facts.\n* **Variable Density:**\n    * *For General Audiences:* Use simple language and analogies.\n    * *For Academic/Technical texts:* Maintain precise terminology but explain difficult concepts.\n* **Formatting:** Use bolding for scannability. Never use dense walls of text.\n\n# Constraints\n* If the text is a **scientific study**, explicitly state the Methodology, Sample Size, and Limitations if mentioned.\n* If the text is **code or technical documentation**, focus on the *functionality* and *use cases*.\n* Do not add outside knowledge unless explicitly asked (stick to the source text).\n\n----------------\n\n'
            'Full text:\n\n' + text
        )
    return prompt

def generate(prompt):
    client = genai.Client(
        api_key=GEMINI_API_KEY,
    )

    model = "gemini-flash-lite-latest"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.OBJECT,
            required=["markdown_content"],
            properties={
                "markdown_content": types.Schema(
                    type=types.Type.STRING,
                ),
            },
        ),
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    try:
        json_object = json.loads(response.text)
        return json_object
    except json.JSONDecodeError:
        print("Failed to decode JSON. Raw response:")
        print(response.text)