-- Initialize database with extensions
-- Mounted by docker-compose postgres service (profiles: core|pgvector|api|full|default).
-- Image: pgvector/pgvector:pg16 — already includes the vector extension package.
--
-- Seed / e2e (host, no live Docker required for unit path):
--   docker compose --profile pgvector up -d
--   PGVECTOR_ENABLED=true python scripts/seed_pgvector.py
--   pytest -q tests/test_pgvector_e2e.py
-- seed_pgvector.py will CREATE EXTENSION vector, ensure parts_catalog.embedding,
-- and upsert PGV-SEED-* rows with fake embeddings when DATABASE_URL/POSTGRES_* reach this DB.
--
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
-- Alias some docs use:
-- CREATE EXTENSION IF NOT EXISTS "pgvector";

-- HNSW index example for pgvector embeddings (run after parts_catalog.embedding exists):
-- CREATE INDEX IF NOT EXISTS idx_parts_catalog_embedding_hnsw
--   ON parts_catalog
--   USING hnsw (embedding vector_cosine_ops)
--   WITH (m = 16, ef_construction = 64);
-- For L2 distance use vector_l2_ops; for inner product use vector_ip_ops.
-- Tune ef_search at query time: SET hnsw.ef_search = 40;
-- Optional: ALTER TABLE parts_catalog ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create initial locations (sample data)
INSERT INTO locations (name, address, city, state, zip_code, phone, email, manager_name, is_active, created_at, updated_at) VALUES
('Downtown Dealership', '123 Main St', 'Downtown', 'CA', '90210', '(555) 123-4567', 'downtown@dealership.com', 'John Smith', true, NOW(), NOW()),
('Westside Location', '456 Oak Ave', 'Westside', 'CA', '90211', '(555) 234-5678', 'westside@dealership.com', 'Jane Doe', true, NOW(), NOW()),
('Eastside Branch', '789 Pine St', 'Eastside', 'CA', '90212', '(555) 345-6789', 'eastside@dealership.com', 'Mike Johnson', true, NOW(), NOW()),
('Northside Auto', '321 Elm St', 'Northside', 'CA', '90213', '(555) 456-7890', 'northside@dealership.com', 'Sarah Wilson', true, NOW(), NOW()),
('Southside Parts', '654 Maple Ave', 'Southside', 'CA', '90214', '(555) 567-8901', 'southside@dealership.com', 'David Brown', true, NOW(), NOW()),
('Central Hub', '987 Cedar Rd', 'Central', 'CA', '90215', '(555) 678-9012', 'central@dealership.com', 'Lisa Davis', true, NOW(), NOW()),
('Metro Location', '147 Birch Ln', 'Metro', 'CA', '90216', '(555) 789-0123', 'metro@dealership.com', 'Robert Miller', true, NOW(), NOW());

-- Create sample customers
INSERT INTO customers (first_name, last_name, email, phone, address, city, state, zip_code, company_name, is_active, created_at, updated_at) VALUES
('Alice', 'Johnson', 'alice.johnson@email.com', '(555) 111-2222', '123 Customer St', 'Customer City', 'CA', '90220', 'Johnson Auto Repair', true, NOW(), NOW()),
('Bob', 'Smith', 'bob.smith@email.com', '(555) 222-3333', '456 Client Ave', 'Client Town', 'CA', '90221', 'Smith Motors', true, NOW(), NOW()),
('Carol', 'Davis', 'carol.davis@email.com', '(555) 333-4444', '789 Buyer Blvd', 'Buyer City', 'CA', '90222', NULL, true, NOW(), NOW());

-- Create sample parts catalog
INSERT INTO parts_catalog (part_number, manufacturer, part_name, description, category, subcategory, make, model, year_from, year_to, msrp, cost, is_active, vector_id, created_at, updated_at) VALUES
('BRK123', 'Brembo', 'Brake Pad Set Front', 'High-performance ceramic brake pads for front wheels', 'Brakes', 'Brake Pads', 'Honda', 'Civic', 2019, 2023, 89.99, 45.00, true, uuid_generate_v4(), NOW(), NOW()),
('FLT456', 'Fram', 'Oil Filter', 'Standard oil filter for 4-cylinder engines', 'Engine', 'Filters', 'Honda', 'Civic', 2019, 2023, 12.99, 6.50, true, uuid_generate_v4(), NOW(), NOW()),
('SPK789', 'NGK', 'Spark Plug Set', 'Iridium spark plugs for improved performance', 'Engine', 'Ignition', 'Honda', 'Civic', 2019, 2023, 24.99, 12.50, true, uuid_generate_v4(), NOW(), NOW()),
('TIR012', 'Michelin', 'Tire 225/60R16', 'All-season radial tire', 'Tires', 'Passenger', 'Honda', 'Civic', 2019, 2023, 149.99, 75.00, true, uuid_generate_v4(), NOW(), NOW());

-- Create sample inventory
INSERT INTO inventory (location_id, part_id, quantity_available, quantity_reserved, quantity_on_order, reorder_point, reorder_quantity, cost, is_active, created_at, updated_at) VALUES
(1, 1, 25, 2, 0, 5, 20, 45.00, true, NOW(), NOW()),
(1, 2, 50, 0, 10, 10, 50, 6.50, true, NOW(), NOW()),
(1, 3, 15, 1, 0, 3, 15, 12.50, true, NOW(), NOW()),
(1, 4, 8, 0, 4, 2, 8, 75.00, true, NOW(), NOW()),
(2, 1, 18, 3, 0, 5, 20, 45.00, true, NOW(), NOW()),
(2, 2, 35, 5, 15, 10, 50, 6.50, true, NOW(), NOW()),
(2, 3, 12, 0, 0, 3, 15, 12.50, true, NOW(), NOW()),
(2, 4, 6, 1, 2, 2, 8, 75.00, true, NOW(), NOW());

-- Create sample suppliers
INSERT INTO suppliers (name, website, contact_email, contact_phone, scrape_enabled, markup_percentage, shipping_cost, minimum_order, is_active, is_trusted, created_at, updated_at) VALUES
('Rock Auto Parts', 'https://www.rockauto.com', 'orders@rockauto.com', '(800) 555-ROCK', true, 15.00, 9.99, 0.00, true, true, NOW(), NOW()),
('AutoZone', 'https://www.autozone.com', 'orders@autozone.com', '(800) 555-AUTO', true, 12.00, 7.99, 0.00, true, true, NOW(), NOW()),
('O''Reilly Auto Parts', 'https://www.oreillyauto.com', 'orders@oreillyauto.com', '(800) 555-OREILLY', true, 10.00, 8.99, 0.00, true, true, NOW(), NOW());

COMMIT;
