// ============================================================
// Agentic AI Knowledge Graph - Neo4j Schema Setup
// Version: 1.0.0
// ============================================================

// ------------------------------------------------------------
// 1. Constraints (Uniqueness)
// ------------------------------------------------------------

// Principle
CREATE CONSTRAINT principle_id IF NOT EXISTS
FOR (p:Principle) REQUIRE p.id IS UNIQUE;

// Standard
CREATE CONSTRAINT standard_id IF NOT EXISTS
FOR (s:Standard) REQUIRE s.id IS UNIQUE;

// StandardVersion
CREATE CONSTRAINT standard_version_id IF NOT EXISTS
FOR (sv:StandardVersion) REQUIRE sv.id IS UNIQUE;

// Method
CREATE CONSTRAINT method_id IF NOT EXISTS
FOR (m:Method) REQUIRE m.id IS UNIQUE;

// Implementation
CREATE CONSTRAINT implementation_id IF NOT EXISTS
FOR (i:Implementation) REQUIRE i.id IS UNIQUE;

// Release
CREATE CONSTRAINT release_id IF NOT EXISTS
FOR (r:Release) REQUIRE r.id IS UNIQUE;

// Document
CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

// DocumentChunk
CREATE CONSTRAINT chunk_id IF NOT EXISTS
FOR (c:DocumentChunk) REQUIRE c.id IS UNIQUE;

// Claim
CREATE CONSTRAINT claim_id IF NOT EXISTS
FOR (cl:Claim) REQUIRE cl.id IS UNIQUE;

// ------------------------------------------------------------
// 2. Indexes (Performance)
// ------------------------------------------------------------

// Principle indexes
CREATE INDEX principle_name IF NOT EXISTS
FOR (p:Principle) ON (p.name);

// Standard indexes
CREATE INDEX standard_name IF NOT EXISTS
FOR (s:Standard) ON (s.name);

CREATE INDEX standard_type IF NOT EXISTS
FOR (s:Standard) ON (s.standard_type);

CREATE INDEX standard_status IF NOT EXISTS
FOR (s:Standard) ON (s.status);

// Method indexes
CREATE INDEX method_name IF NOT EXISTS
FOR (m:Method) ON (m.name);

CREATE INDEX method_family IF NOT EXISTS
FOR (m:Method) ON (m.method_family);

CREATE INDEX method_type IF NOT EXISTS
FOR (m:Method) ON (m.method_type);

CREATE INDEX method_granularity IF NOT EXISTS
FOR (m:Method) ON (m.granularity);

CREATE INDEX method_year IF NOT EXISTS
FOR (m:Method) ON (m.year_introduced);

CREATE INDEX method_maturity IF NOT EXISTS
FOR (m:Method) ON (m.maturity);

// Implementation indexes
CREATE INDEX impl_name IF NOT EXISTS
FOR (i:Implementation) ON (i.name);

CREATE INDEX impl_type IF NOT EXISTS
FOR (i:Implementation) ON (i.impl_type);

CREATE INDEX impl_status IF NOT EXISTS
FOR (i:Implementation) ON (i.status);

CREATE INDEX impl_maintainer IF NOT EXISTS
FOR (i:Implementation) ON (i.maintainer);

// Release indexes
CREATE INDEX release_version IF NOT EXISTS
FOR (r:Release) ON (r.version);

CREATE INDEX release_status IF NOT EXISTS
FOR (r:Release) ON (r.status);

// Document indexes
CREATE INDEX doc_title IF NOT EXISTS
FOR (d:Document) ON (d.title);

CREATE INDEX doc_type IF NOT EXISTS
FOR (d:Document) ON (d.doc_type);

CREATE INDEX doc_year IF NOT EXISTS
FOR (d:Document) ON (d.year);

// DocumentChunk indexes
CREATE INDEX chunk_document IF NOT EXISTS
FOR (c:DocumentChunk) ON (c.document);

CREATE INDEX chunk_hash IF NOT EXISTS
FOR (c:DocumentChunk) ON (c.content_hash);

// Claim indexes
CREATE INDEX claim_predicate IF NOT EXISTS
FOR (cl:Claim) ON (cl.predicate);

CREATE INDEX claim_subject IF NOT EXISTS
FOR (cl:Claim) ON (cl.subject);

CREATE INDEX claim_object IF NOT EXISTS
FOR (cl:Claim) ON (cl.object);

CREATE INDEX claim_confidence IF NOT EXISTS
FOR (cl:Claim) ON (cl.confidence);

// ------------------------------------------------------------
// 3. Full-text Search Indexes (Optional)
// ------------------------------------------------------------

// Method full-text search
CREATE FULLTEXT INDEX method_fulltext IF NOT EXISTS
FOR (m:Method) ON EACH [m.name, m.description];

// Document full-text search
CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS
FOR (d:Document) ON EACH [d.title, d.abstract];

// DocumentChunk full-text search
CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
FOR (c:DocumentChunk) ON EACH [c.content];

// ------------------------------------------------------------
// 4. Vector Index (for embeddings - Neo4j 5.15+)
// ------------------------------------------------------------

// Note: Uncomment if using Neo4j 5.15+ with vector support
// CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
// FOR (c:DocumentChunk) ON (c.embedding_vector)
// OPTIONS {indexConfig: {
//   `vector.dimensions`: 1536,
//   `vector.similarity_function`: 'cosine'
// }};
