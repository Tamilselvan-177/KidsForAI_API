from textblob import TextBlob
from spellchecker import SpellChecker

# Input text with mistakes
text = "Ths is an exampel of splling corection"

# Step 1: TextBlob for best correction
blob = TextBlob(text)
best_correction = blob.correct()

# Step 2: PySpellChecker for multiple suggestions
spell = SpellChecker()

# Find misspelled words
misspelled = spell.unknown(text.split())

suggestions = {}
for word in misspelled:
    suggestions[word] = spell.candidates(word)  # Get multiple possible corrections

# Output results
print("Original Text: ", text)
print("Best Correction: ", best_correction)
print("\nSuggestions for each wrong word:")
for wrong, sugg in suggestions.items():
    print(f"{wrong} → {', '.join(sugg)}")
