import openai
from django.conf import settings
import logging

# Add your OpenAI API key
client = openai.OpenAI(
  organization=settings.OPENAI_ORGANIZATION_KEY,
  project=settings.OPENAI_PROJECT_ID,
  api_key=settings.OPENAI_SECRET_KEY,
)
logger = logging.getLogger('spite')

def generate_summary(prompt, max_chars=None):
    logger.info(f'Prompt: {prompt}')
    if max_chars == None:
        # Calculate available tokens for response
        MAX_TOKENS = 8192  # Total token limit for GPT-4
        input_tokens = len(prompt) // 4  # Approximate token count for the input
        max_response_tokens = MAX_TOKENS - input_tokens
    else:
        max_response_tokens = max_chars // 4
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "U r a chinese emperor and the posters in this forum are your subjects. Issue your pronouncements upon them in the form of proverbs. Try not to repeat things from memory"},
                {"role": "user", "content": prompt},
            ], 
            max_tokens = max_response_tokens,
        )
        summary = response.choices[0].message.content
        logger.info(f'Summary: {summary}')
        return summary
    except Exception as e:
        logger.info(f"Error generating summary: {e}")