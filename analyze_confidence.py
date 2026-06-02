from pinecone_client import get_index
from openai import OpenAI
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def analyze_confidence(question):
    """Analyze why confidence score is what it is"""
    print("\n" + "="*80)
    print(f"CONFIDENCE SCORE ANALYSIS")
    print("="*80)
    print(f"\nQuestion: '{question}'")
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        index = get_index()
        
        # Get embedding
        response = client.embeddings.create(
            input=question,
            model="text-embedding-3-small"
        )
        query_vec = response.data[0].embedding
        
        # Query Pinecone
        results = index.query(
            vector=query_vec,
            top_k=10,
            include_metadata=True
        )
        
        if not results.get("matches"):
            print("\n❌ No matches found!")
            return
        
        print(f"\n✅ Found {len(results['matches'])} matches")
        print("\n" + "="*80)
        print("TOP 10 MATCHES WITH SCORES")
        print("="*80)
        
        for i, match in enumerate(results["matches"], 1):
            score = match.get("score", 0.0)
            metadata = match.get("metadata", {})
            source = metadata.get("source", "Unknown")
            page = metadata.get("page", "N/A")
            text = metadata.get("text", "")
            
            # Score interpretation
            if score >= 0.9:
                interpretation = "🟢 EXCELLENT - Near perfect match"
            elif score >= 0.7:
                interpretation = "🟢 GOOD - Strong semantic match"
            elif score >= 0.5:
                interpretation = "🟡 MODERATE - Partial match"
            elif score >= 0.3:
                interpretation = "🟠 WEAK - Loosely related"
            else:
                interpretation = "🔴 POOR - Barely related"
            
            print(f"\n--- Match {i} ---")
            print(f"Score: {score:.4f} ({score*100:.2f}%) - {interpretation}")
            print(f"Source: {source} - Page {page}")
            print(f"Text Preview (first 200 chars):")
            print(f"  {text[:200]}...")
            
            if i == 1:
                print(f"\n💡 This is your CONFIDENCE SCORE: {score*100:.1f}%")
        
        # Analysis
        print("\n" + "="*80)
        print("SCORE ANALYSIS")
        print("="*80)
        
        top_score = results["matches"][0].get("score", 0.0)
        
        print(f"\n📊 Your Confidence Score: {top_score*100:.1f}%")
        print(f"\n🔍 Why this score?")
        
        if top_score >= 0.9:
            print("   ✅ Excellent! Your question closely matches the document content.")
            print("   - Question words align well with document terminology")
            print("   - Specific topic found in knowledge base")
        elif top_score >= 0.7:
            print("   ✅ Good match! The document has relevant information.")
            print("   - Semantic meaning is captured")
            print("   - Some word differences but concept matches")
        elif top_score >= 0.5:
            print("   ⚠️ Moderate match. Reasons could be:")
            print("   - Question is too general/broad")
            print("   - Document uses different terminology")
            print("   - Content is split across multiple chunks")
            print("   - Question asks about a topic not deeply covered")
        elif top_score >= 0.3:
            print("   ⚠️ Weak match. Likely reasons:")
            print("   - Question topic is barely covered in documents")
            print("   - Very different vocabulary used")
            print("   - Question is too vague")
        else:
            print("   ❌ Poor match. The knowledge base likely doesn't have this information.")
        
        # Recommendations
        print(f"\n💡 How to improve confidence score:")
        
        if top_score < 0.7:
            print("   1. Be more specific in your question")
            print("   2. Use terminology from the document")
            print("   3. Ask about specific topics/sections")
            print("   4. Break complex questions into simpler ones")
            print(f"\n   Example improvements:")
            if "best practices" in question.lower():
                print("   - Instead of: 'What are best practices?'")
                print("   - Try: 'What does Item 1 recommend about constructors?'")
                print("   - Or: 'What are the guidelines for using static factory methods?'")
        else:
            print("   ✅ Your question is already well-formed!")
        
        # Compare with specific question
        print("\n" + "="*80)
        print("COMPARISON: GENERAL VS SPECIFIC QUESTION")
        print("="*80)
        
        specific_question = "What does the book say about the builder pattern?"
        print(f"\nTesting specific question: '{specific_question}'")
        
        response2 = client.embeddings.create(
            input=specific_question,
            model="text-embedding-3-small"
        )
        query_vec2 = response2.data[0].embedding
        
        results2 = index.query(
            vector=query_vec2,
            top_k=3,
            include_metadata=True
        )
        
        if results2.get("matches"):
            specific_score = results2["matches"][0].get("score", 0.0)
            print(f"\nSpecific Question Score: {specific_score*100:.1f}%")
            print(f"Your Question Score: {top_score*100:.1f}%")
            print(f"Difference: {(specific_score - top_score)*100:.1f}%")
            
            if specific_score > top_score:
                print(f"\n✅ Specific questions get higher scores!")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"\n📌 Key Points:")
        print(f"   - Confidence score = Semantic similarity to document content")
        print(f"   - 90%+ = Near exact match (rare)")
        print(f"   - 70-89% = Strong match (good)")
        print(f"   - 50-69% = Moderate match (acceptable)")
        print(f"   - Below 50% = Weak match (may not have info)")
        print(f"\n   Your score of {top_score*100:.1f}% means:")
        if top_score >= 0.7:
            print(f"   ✅ The system found relevant information!")
        elif top_score >= 0.5:
            print(f"   ⚠️ Information found but not a perfect match")
        else:
            print(f"   ❌ Limited information available on this topic")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_multiple_questions():
    """Test different types of questions"""
    print("\n" + "="*80)
    print("TESTING DIFFERENT QUESTION TYPES")
    print("="*80)
    
    questions = [
        ("General", "What are best practices?"),
        ("Specific", "What does Item 2 say about builder pattern?"),
        ("Very Specific", "What are the advantages of static factory methods over constructors?"),
        ("Vague", "Tell me about Java"),
        ("Irrelevant", "What is the weather today?")
    ]
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    index = get_index()
    
    print("\n")
    for q_type, question in questions:
        response = client.embeddings.create(
            input=question,
            model="text-embedding-3-small"
        )
        query_vec = response.data[0].embedding
        
        results = index.query(
            vector=query_vec,
            top_k=1,
            include_metadata=True
        )
        
        if results.get("matches"):
            score = results["matches"][0].get("score", 0.0)
            print(f"{q_type:15} | Score: {score*100:5.1f}% | Question: {question}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        analyze_confidence(question)
    else:
        # Default test
        print("\nUsage: python analyze_confidence.py \"Your question here\"")
        print("\nRunning default tests...\n")
        test_multiple_questions()
        print("\n\nNow analyzing a sample question in detail:\n")
        analyze_confidence("What are the best practices for Java?")
