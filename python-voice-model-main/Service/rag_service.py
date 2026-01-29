from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import TranscriptionFrame
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

class RAGService(FrameProcessor):
    def __init__(self, context, **kwargs):
        super().__init__(**kwargs)
        self.context = context
        
        # Initialize vector store
        embeddings = OpenAIEmbeddings()
        self.vector_store = PineconeVectorStore(
            index_name="your-index", 
            embedding=embeddings
        )
    
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TranscriptionFrame):
            # Query vector database
            docs = self.vector_store.similarity_search(frame.text, k=2)
            
            # Inject context as system message
            if docs:
                context_text = "\n".join([doc.page_content for doc in docs])
                self.context.add_message({
                    "role": "system",
                    "content": f"<context>{context_text}</context>"
                })
        
        await self.push_frame(frame, direction)
