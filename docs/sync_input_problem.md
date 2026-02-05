Current Implementation (Automatic)                                                      
                                                                                          
  User: "What is transformer architecture?"                                               
           ↓                                                                              
      [Web Search] → Tavily returns arxiv result                                          
           ↓                                                                              
      [_persist_web_results()] → ChromaDB                                                 
                                                                                          
      ID: web:a1b2c3d4e5f6:0                                                              
      Metadata:                                                                           
        source_type: "web_search"                                                         
        source_url: "https://arxiv.org/abs/1706.03762"                                    
        node_id: ""        ← NOT linked to KG                                             
        node_label: ""     ← NOT linked to KG                                             
        search_query: "What is transformer architecture?"                                 
                                                                                          
  VDB: Done automatically. Web results are persisted to ChromaDB.                         
                                                                                          
  KG: NOT done. The node_id and node_label are empty strings.                             
                                                                                          
  What's Missing (Phase 3b)                                                               
                                                                                          
  To add "Transformer" to the KG, we need:                                                
                                                                                          
  1. Entity Extraction from web result                                                    
     - Detect: "Transformer" is a Method                                                  
     - Detect: "Vaswani et al. 2017" is a Document                                        
     - Detect: Addresses "Perception", "Reasoning" principles                             
                                                                                          
  2. User Approval UI                                                                     
     ┌─────────────────────────────────────────┐                                          
     │ Add to Knowledge Graph?                 │                                          
     │                                         │                                          
     │ [Method] Transformer                    │                                          
     │ Description: Self-attention mechanism...│                                          
     │ Family: prompting_decoding              │                                          
     │ Addresses: Perception, Reasoning        │                                          
     │                                         │                                          
     │ [Add to KG]  [Skip]  [Edit first]       │                                          
     └─────────────────────────────────────────┘                                          
                                                                                          
  3. If approved:                                                                         
     - Create Neo4j node: (m:Method {id: "m:transformer", ...})                           
     - Create relationships: (m)-[:ADDRESSES]->(p:Principle)                              
     - Update VDB entry: node_id="m:transformer", node_label="Method"                     
     - Or: Delete web:* entry, create kg:m:transformer entry                              
                                                                                          
  The Gap                                                                                 
                                                                                          
  # Current web_search.py:78-131                                                          
  def _persist_web_results(results, query):                                               
      metadata = {                                                                        
          "source_type": "web_search",                                                    
          "node_id": "",      # ← Always empty                                            
          "node_label": "",   # ← Always empty                                            
          ...                                                                             
      }                                                                                   
                                                                                          
  There's no:                                                                             
  1. Entity extraction from web content                                                   
  2. Mapping to KG schema (Method/Implementation/Document)                                
  3. User approval workflow                                                               
  4. Neo4j write operation                                                                
  5. VDB entry promotion (web:* → kg:*)                                                   
                                                                                          
  Proposed Flow (Phase 3b)                                                                
                                                                                          
  [Web Search Result]                                                                     
         ↓                                                                                
  [Entity Extractor] ← LLM classifies: Method? Implementation? Document?                  
         ↓                                                                                
  [Candidate Generator] ← Proposes node properties + relationships                        
         ↓                                                                                
  [User Approval UI] ← Streamlit shows diff, user approves/edits                          
         ↓                                                                                
  [KG Writer] ← Creates Neo4j node + relationships                                        
         ↓                                                                                
  [VDB Promoter] ← Deletes web:* entry, runs generate_embeddings for new node             
                                                                                          
  Should I design the detailed implementation plan for this Phase 3b workflow?            
                                                                                          
❯ Then will VDB embed whole texts from transformer paper? And let's imagine once          
  more. I brought some papers to data folder or somewhere around. How can I store to      
  vdb, kg and sync them? Can I sync it even? Should I do it manually?                     
                                                                                          
⏺ Two separate questions here. Let me address both.                                       
                                                                                          
  1. Will VDB embed the whole Transformer paper?                                          
                                                                                          
  No. Currently only Tavily snippets (~200-500 words) get embedded.                       
                                                                                          
  Tavily API Response:                                                                    
  {                                                                                       
    "content": "The Transformer architecture uses self-attention...",  ← ~300 words       
  snippet                                                                                 
    "raw_content": null  ← We don't request full text                                     
  }                                                                                       
           ↓                                                                              
  ChromaDB: Only the snippet is embedded                                                  
                                                                                          
  For full paper embedding, you'd need:                                                   
  - PDF parsing (PyMuPDF, pdfplumber)                                                     
  - Chunking (500-1000 tokens with overlap)                                               
  - Multiple VDB entries per paper: doc:transformer:0, doc:transformer:1, ...             
                                                                                          
  2. Local Papers → VDB + KG Sync?                                                        
                                                                                          
  Currently: Manual and fragmented.                                                       
                                                                                          
  You have: data/papers/attention-is-all-you-need.pdf                                     
                                                                                          
  Current options:                                                                        
  ┌─────────────────────────────────────────────────────────┐                             
  │ Option A: Manual Neo4j + auto VDB                       │                             
  │                                                         │                             
  │ 1. Manually write Cypher:                               │                             
  │    CREATE (d:Document {id: "doc:transformer-2017", ...})│                             
  │    CREATE (d)-[:PROPOSES]->(m:Method {id: "m:transformer"})│                          
  │                                                         │                             
  │ 2. Run: poetry run python scripts/generate_embeddings.py│                             
  │    → Only embeds node description (1-2 sentences)       │                             
  │    → NOT the full paper text                            │                             
  └─────────────────────────────────────────────────────────┘                             
                                                                                          
  ┌─────────────────────────────────────────────────────────┐                             
  │ Option B: Direct VDB only (no KG)                       │                             
  │                                                         │                             
  │ Write custom script to:                                 │                             
  │ 1. Parse PDF → chunks                                   │                             
  │ 2. Embed chunks                                         │                             
  │ 3. Store with ID: doc:{doc_id}:{chunk_index}            │                             
  │                                                         │                             
  │ Problem: Not linked to KG (node_id="")                  │                             
  └─────────────────────────────────────────────────────────┘                             
                                                                                          
  The gap: No unified pipeline exists.                                                    
                                                                                          
  What's Needed: Document Ingestion Pipeline                                              
                                                                                          
  data/papers/                                                                            
  ├── attention-is-all-you-need.pdf                                                       
  ├── react-2022.pdf                                                                      
  └── manifest.yaml  ← metadata file                                                      
                                                                                          
  manifest.yaml:                                                                          
  ─────────────────                                                                       
  - file: attention-is-all-you-need.pdf                                                   
    doc_id: doc:transformer-2017                                                          
    title: "Attention Is All You Need"                                                    
    authors: ["Vaswani et al."]                                                           
    year: 2017                                                                            
    proposes:                                                                             
      - id: m:transformer                                                                 
        name: Transformer                                                                 
        family: prompting_decoding                                                        
        addresses: [p:perception, p:reasoning]                                            
                                                                                          
  poetry run python scripts/ingest_papers.py                                              
                                                                                          
  [1] Parse manifest.yaml                                                                 
  [2] For each paper:                                                                     
      ├─ Create/update Neo4j Document node                                                
      ├─ Create/update proposed Method nodes                                              
      ├─ Create relationships (PROPOSES, ADDRESSES)                                       
      ├─ Parse PDF → chunks                                                               
      ├─ Embed chunks                                                                     
      └─ Store in VDB: doc:{doc_id}:{chunk_index}                                         
          metadata: node_id=doc:transformer-2017, node_label=Document                     
  [3] Update embedding_hashes.json                                                        
                                                                                          
  Summary                                                                                 
  ┌───────────────────────────────┬──────────────────────────────────────────────┐        
  │           Question            │                Current State                 │        
  ├───────────────────────────────┼──────────────────────────────────────────────┤        
  │ Web search → full paper text? │ No, only snippets                            │        
  ├───────────────────────────────┼──────────────────────────────────────────────┤        
  │ Local papers → VDB?           │ No pipeline                                  │        
  ├───────────────────────────────┼──────────────────────────────────────────────┤        
  │ Local papers → KG?            │ Manual Cypher only                           │        
  ├───────────────────────────────┼──────────────────────────────────────────────┤        
  │ Sync VDB ↔ KG?                │ One-way: KG → VDB via generate_embeddings.py │        
  ├───────────────────────────────┼──────────────────────────────────────────────┤        
  │ Can you sync local papers?    │ No, must do manually                         │        
  └───────────────────────────────┴──────────────────────────────────────────────┘  