import re
import language_tool_python
from typing import List


def format(text: str) -> str:
    """
    Formats Terms of Service text into professional paragraphs with:
    - Grammar correction
    - Proper capitalization
    - Logical paragraph breaks
    - Consistent spacing
    """
    # 1. Initial cleaning and grammar check
    text = fix_repeats(text)

    # 2. Capitalization fixes
    text = basic_capitalization(text)

    # 3. Paragraph structuring
    paragraphs = structure_paragraphs(text)

    # 4. Final cleanup and grammar check
    return final_cleanup(paragraphs)


def fix_repeats(text: str) -> str:
    """Fix repeated words and basic grammar issues."""
    # Fix immediate word repetitions (e.g., "changed or changed")
    text = re.sub(r"\b(\w+)\b\s+(or|and|,)\s+\b\1\b", r"\1", text, flags=re.IGNORECASE)

    # General grammar correction
    tool = language_tool_python.LanguageTool("en-US")
    return tool.correct(text)


def basic_capitalization(text: str) -> str:
    """Ensure proper capitalization throughout the text."""
    # Capitalize 'I' and sentence starters
    text = re.sub(r"\bi\b", "I", text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)]
    sentences = [s[0].upper() + s[1:] if s else s for s in sentences]
    return " ".join(sentences)


def structure_paragraphs(text: str) -> List[str]:
    """
    Organizes text into logical paragraphs based on content.
    Groups related clauses together for better readability.
    """
    # Split at major section starters
    sections = re.split(r"(?<=[.!?])\s+(?=[A-Z][a-z])", text)

    paragraphs = []
    current_para = []

    for sentence in sections:
        # New paragraph for major topics
        if any(
            trigger in sentence.lower()
            for trigger in ["terms of", "privacy", "if you", "you agree", "you must"]
        ):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
        current_para.append(sentence)

    if current_para:
        paragraphs.append(" ".join(current_para))

    return paragraphs


def final_cleanup(paragraphs: List[str]) -> str:
    """Applies final formatting touches and grammar check."""
    # Join with double line breaks
    formatted_text = "\n\n".join(paragraphs)

    # Ensure space after punctuation
    formatted_text = re.sub(r"([.!?])([A-Z])", r"\1 \2", formatted_text)

    # Final grammar check
    tool = language_tool_python.LanguageTool("en-US")
    matches = tool.check(formatted_text)
    return language_tool_python.utils.correct(formatted_text, matches)


# from datasets import load_dataset
from transformers import T5Tokenizer, T5ForConditionalGeneration


# def load_cuad_dataset():
#     """Load the CUAD dataset"""
#     dataset = load_dataset("theatticusproject/cuad-qa")
#     return dataset


def split_contract(text, chunk_size=128, overlap=32):
    """
    Split contract text into overlapping chunks
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)

    return chunks


def initialize_summarizer():
    """Initialize the T5 summarization model"""
    model_path = "t5_legal_simplification_v9"
    tokenizer = T5Tokenizer.from_pretrained(model_path)
    model = T5ForConditionalGeneration.from_pretrained(model_path)
    return tokenizer, model


def generate_summary(text, tokenizer, model):
    """Generate summary for given text using the model"""
    chunks = split_contract(text)
    summaries = []

    for chunk in chunks:
        input_text = "Rewrite the following sentences in a concise and clear summary while retaining the general meaning. Ensure the summary remains factual, neutral, and avoids exaggeration or speculative language: " + chunk
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        output = model.generate(**inputs, max_length=200)
        summary = tokenizer.decode(output[0], skip_special_tokens=True)
        summaries.append(summary)

    return "\n".join(summaries)
