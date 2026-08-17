MAP_SUMMARY_PROMPT = """Summarize the following document excerpt concise and objectively. Focus on key technical facts, operational procedures, requirements, and safety warnings.

Document Excerpt:
{text}

Concise Summary:"""

REDUCE_SUMMARY_PROMPT = """You are a technical document summarizer. Synthesize the following intermediate summaries from a document into a structured final summary.

Intermediate Summaries:
{intermediate_summaries}

Target Length Mode: {summary_type} (short = ~150 words, medium = ~300 words, detailed = ~600 words)

Format your response exactly with the following clear section headers:
## OVERVIEW
[High-level summary of the document]

## KEY POINTS
- [Key point 1]
- [Key point 2]

## IMPORTANT PROCEDURES
- [Procedure 1]

## WARNINGS AND SAFETY
- [Warning/Safety note if present, or None]

## CONCLUSION
[Concluding statement]
"""
