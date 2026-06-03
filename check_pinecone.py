from pinecone_client import get_index
from rag import retrieve
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def check_pinecone_status():
    """Check if Pinecone has the PDF content"""
    print("\n" + "="*80)
    print("PINECONE INDEX STATUS CHECK")
    print("="*80)
    
    try:
        # Get the index
        index = get_index()
        
        # Get index stats
        stats = index.describe_index_stats()
        
        print(f"\n✅ Successfully connected to Pinecone!")
        print(f"\n📊 Index Statistics:")
        print(f"   - Total Vectors: {stats.get('total_vector_count', 0)}")
        print(f"   - Index Dimension: {stats.get('dimension', 'N/A')}")
        
        if stats.get('namespaces'):
            print(f"   - Namespaces: {stats['namespaces']}")
        
        total_vectors = stats.get('total_vector_count', 0)
        
        if total_vectors == 0:
            print("\n❌ WARNING: No vectors found in Pinecone!")
            print("   The PDF might not have been uploaded to Pinecone.")
            print("\n💡 To upload the PDF to Pinecone:")
            print("   1. Run the React app from frontend/: npm run dev")
            print("   2. Upload the PDF using the sidebar")
            print("   3. Click 'Upload to Pinecone' button")
            return False
        else:
            print(f"\n✅ Pinecone has {total_vectors} vectors (chunks) from your documents!")
            
            # Test retrieval
            print("\n" + "="*80)
            print("TESTING RETRIEVAL")
            print("="*80)
            
            test_query = "What are the best practices in Java?"
            print(f"\nTest Query: '{test_query}'")
            print("\nRetrieving relevant chunks...")
            
            context = retrieve(test_query)
            
            if context:
                print(f"\n✅ Successfully retrieved context!")
                print(f"\nFirst 500 characters of retrieved context:")
                print("-" * 80)
                print(context[:500] + "...")
                print("-" * 80)
                return True
            else:
                print("\n❌ No context retrieved!")
                return False
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n💡 Make sure:")
        print("   1. PINECONE_API_KEY is set in .env")
        print("   2. PINECONE_INDEX_NAME is set in .env")
        print("   3. The index exists in your Pinecone account")
        return False

def check_indexed_files():
    """Check which files are marked as indexed locally"""
    print("\n" + "="*80)
    print("LOCAL INDEXED FILES")
    print("="*80)
    
    try:
        import json
        indexed_file = os.path.join(BASE_DIR, "indexed_docs.json")
        
        if os.path.exists(indexed_file):
            with open(indexed_file, 'r') as f:
                indexed_docs = json.load(f)
            
            if indexed_docs:
                print(f"\n✅ Found {len(indexed_docs)} indexed file(s):")
                for i, doc in enumerate(indexed_docs, 1):
                    print(f"   {i}. {doc}")
            else:
                print("\n⚠️ No files marked as indexed locally")
        else:
            print("\n⚠️ indexed_docs.json not found")
            
    except Exception as e:
        print(f"\n❌ Error reading indexed files: {str(e)}")

def main():
    print("\n" + "="*80)
    print("KNOWLEDGE ASSISTANT - PINECONE VERIFICATION")
    print("="*80)
    
    # Check local indexed files
    check_indexed_files()
    
    # Check Pinecone status
    pinecone_ok = check_pinecone_status()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if pinecone_ok:
        print("\n✅ Everything looks good! Your PDF is in Pinecone and ready to use.")
        print("\n🚀 You can now:")
        print("   1. Test the API: python test_effective_java.py")
        print("   2. Use the React app from frontend/: npm run dev")
        print("   3. Integrate with external platforms (Teams, Slack, WhatsApp)")
    else:
        print("\n⚠️ Action Required:")
        print("   1. Run the React app from frontend/: npm run dev")
        print("   2. Upload your PDF using the sidebar")
        print("   3. Click 'Upload to Pinecone' button")
        print("   4. Run this script again to verify")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
