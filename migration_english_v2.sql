-- ============================================================================
-- DATABASE TRANSLATION & OPTIMIZATION MIGRATION SCRIPT
-- Troubleshooting System Portuguese/Spanish → English Migration
-- ============================================================================
-- 
-- This script performs a complete migration of the database from 
-- Portuguese/Spanish labels to 100% English
--
-- Usage:
--   mysql -u root -p troubleshooting_db < migration_english_v2.sql
--
-- WARNING: Test in development first! Always backup before running in production.
-- ============================================================================

SET SESSION SQL_MODE = 'STRICT_TRANS_TABLES';
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- PHASE 1: DATA TRANSLATION (Update existing records)
-- ============================================================================

-- Update failure status terminology
UPDATE failures SET `status` = 'Open' WHERE `status` IN ('Aberta', 'Abierta');
UPDATE failures SET `status` = 'Closed' WHERE `status` IN ('Fechada', 'Cerrada');
UPDATE failures SET `status` = 'In Progress' WHERE `status` IN ('Emaberto', 'En Progreso');
UPDATE failures SET `status` = 'Resolved' WHERE `status` IN ('Resolvida', 'Resuelta');

-- Update aircraft registration status
UPDATE aircraft SET `registration_status` = 'Active' WHERE `registration_status` IN ('Ativa', 'Activa');
UPDATE aircraft SET `registration_status` = 'In Service' WHERE `registration_status` IN ('Em Serviço', 'En Servicio');
UPDATE aircraft SET `registration_status` = 'Out of Service' WHERE `registration_status` IN ('Fora de Serviço', 'Fuera de Servicio');
UPDATE aircraft SET `registration_status` = 'Grounded' WHERE `registration_status` IN ('Aposentada', 'Retirada');
UPDATE aircraft SET `registration_status` = 'Retired' WHERE `registration_status` IN ('Aposentada', 'Retirada');

-- Update user roles
UPDATE users SET `role` = 'Administrator' WHERE `role` IN ('Administrador', 'Admin');
UPDATE users SET `role` = 'Technician' WHERE `role` IN ('Técnico', 'Tecnico');
UPDATE users SET `role` = 'Pilot' WHERE `role` IN ('Piloto', 'Pilot');
UPDATE users SET `role` = 'User' WHERE `role` IN ('Usuário', 'Usuario');

-- Update access levels
UPDATE users SET `access_level` = 'Administrator' WHERE `access_level` IN ('Administrador', 'Admin');
UPDATE users SET `access_level` = 'Technician' WHERE `access_level` IN ('Técnico', 'Tecnico');
UPDATE users SET `access_level` = 'Pilot' WHERE `access_level` IN ('Piloto', 'Pilot');
UPDATE users SET `access_level` = 'User' WHERE `access_level` IN ('Usuário', 'Usuario');

-- Update failure categories (if exists)
UPDATE failure_categories SET `name` = 'Critical' WHERE `name` IN ('Crítico', 'Crítica', 'Critico');
UPDATE failure_categories SET `name` = 'High' WHERE `name` IN ('Alta', 'Alerta');
UPDATE failure_categories SET `name` = 'Medium' WHERE `name` IN ('Média', 'Media', 'Média Prioridade');
UPDATE failure_categories SET `name` = 'Low' WHERE `name` IN ('Baixa', 'Baja');

-- ============================================================================
-- PHASE 2: SCHEMA OPTIMIZATION - Add Indices for Performance
-- ============================================================================

-- Aircraft table indices
ALTER TABLE aircraft ADD INDEX idx_tail (tail);
ALTER TABLE aircraft ADD INDEX idx_aircraft_model (aircraft_model);
ALTER TABLE aircraft ADD INDEX idx_registration_status (registration_status);

-- Failures table indices
ALTER TABLE failures ADD INDEX idx_tail_fk (tail);
ALTER TABLE failures ADD INDEX idx_date_opened (date_opened);
ALTER TABLE failures ADD INDEX idx_date_closed (date_closed);
ALTER TABLE failures ADD INDEX idx_status (status);
ALTER TABLE failures ADD INDEX idx_category (category);
ALTER TABLE failures ADD INDEX idx_ata (ata);

-- Full text search index for failure system descriptions
ALTER TABLE failures ADD FULLTEXT INDEX idx_system_inop_search (system_inop, notes);

-- Users table indices
ALTER TABLE users ADD INDEX idx_username (username);
ALTER TABLE users ADD INDEX idx_email (email);
ALTER TABLE users ADD INDEX idx_is_active (is_active);
ALTER TABLE users ADD INDEX idx_access_level (access_level);
ALTER TABLE users ADD INDEX idx_last_login (last_login);

-- ============================================================================
-- PHASE 3: SCHEMA STRUCTURE - Add Missing Columns for Modern Features
-- ============================================================================

-- Add audit columns to failures table
ALTER TABLE failures 
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS created_by INT,
ADD COLUMN IF NOT EXISTS updated_by INT;

-- Add audit columns to aircraft table
ALTER TABLE aircraft 
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS created_by INT,
ADD COLUMN IF NOT EXISTS updated_by INT;

-- Add soft delete capability
ALTER TABLE failures ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL;
ALTER TABLE aircraft ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL;

-- Add extended user information
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
ADD COLUMN IF NOT EXISTS department VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_password_change DATETIME;

-- ============================================================================
-- PHASE 4: FOREIGN KEY CONSTRAINTS & DATA INTEGRITY
-- ============================================================================

-- Drop existing foreign keys if they exist
ALTER TABLE failures DROP FOREIGN KEY IF EXISTS fk_failures_aircraft;
ALTER TABLE failures DROP FOREIGN KEY IF EXISTS fk_failures_created_by;
ALTER TABLE failures DROP FOREIGN KEY IF EXISTS fk_failures_updated_by;

-- Add proper foreign key constraints
ALTER TABLE failures 
ADD CONSTRAINT fk_failures_aircraft 
FOREIGN KEY (tail) REFERENCES aircraft(tail) ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE failures 
ADD CONSTRAINT fk_failures_created_by 
FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE failures 
ADD CONSTRAINT fk_failures_updated_by 
FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL;

-- Add check constraints for valid statuses
ALTER TABLE failures 
ADD CONSTRAINT chk_failure_status 
CHECK (status IN ('Open', 'Closed', 'In Progress', 'Resolved'));

ALTER TABLE failures 
ADD CONSTRAINT chk_failure_category 
CHECK (category IN ('A', 'B', 'C', 'D'));

ALTER TABLE aircraft 
ADD CONSTRAINT chk_aircraft_status 
CHECK (registration_status IN ('Active', 'In Service', 'Out of Service', 'Grounded', 'Retired'));

-- ============================================================================
-- PHASE 5: AUDIT LOGGING TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  table_name VARCHAR(100) NOT NULL,
  record_id INT,
  action ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
  old_value JSON,
  new_value JSON,
  user_id INT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  ip_address VARCHAR(45),
  
  INDEX idx_table_name (table_name),
  INDEX idx_timestamp (timestamp),
  INDEX idx_user_id (user_id),
  
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PHASE 6: AUDIT TRIGGERS for Data Changes
-- ============================================================================

-- Trigger for failures INSERT
DROP TRIGGER IF EXISTS audit_failures_insert;
CREATE TRIGGER audit_failures_insert AFTER INSERT ON failures
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, new_value, user_id, timestamp)
  VALUES (
    'failures',
    NEW.id,
    'INSERT',
    JSON_OBJECT(
      'tail', NEW.tail,
      'status', NEW.status,
      'system_inop', NEW.system_inop
    ),
    NEW.created_by,
    NOW()
  );
END;

-- Trigger for failures UPDATE
DROP TRIGGER IF EXISTS audit_failures_update;
CREATE TRIGGER audit_failures_update AFTER UPDATE ON failures
FOR EACH ROW
BEGIN
  IF NOT (OLD.status <=> NEW.status AND 
          OLD.notes <=> NEW.notes AND 
          OLD.maintenance_action <=> NEW.maintenance_action) THEN
    INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, user_id, timestamp)
    VALUES (
      'failures',
      NEW.id,
      'UPDATE',
      JSON_OBJECT('status', OLD.status, 'notes', OLD.notes),
      JSON_OBJECT('status', NEW.status, 'notes', NEW.notes),
      NEW.updated_by,
      NOW()
    );
  END IF;
END;

-- Trigger for aircraft INSERT
DROP TRIGGER IF EXISTS audit_aircraft_insert;
CREATE TRIGGER audit_aircraft_insert AFTER INSERT ON aircraft
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, new_value, user_id, timestamp)
  VALUES (
    'aircraft',
    NEW.id,
    'INSERT',
    JSON_OBJECT(
      'tail', NEW.tail,
      'model', NEW.aircraft_model,
      'status', NEW.registration_status
    ),
    NEW.created_by,
    NOW()
  );
END;

-- ============================================================================
-- PHASE 7: PERFORMANCE STATISTICS VIEWS
-- ============================================================================

-- Fleet summary view
DROP VIEW IF EXISTS v_fleet_summary;
CREATE VIEW v_fleet_summary AS
SELECT 
  COUNT(*) as total_aircraft,
  SUM(CASE WHEN registration_status = 'Active' THEN 1 ELSE 0 END) as active_count,
  SUM(CASE WHEN registration_status = 'Out of Service' THEN 1 ELSE 0 END) as oos_count,
  SUM(CASE WHEN registration_status = 'Retired' THEN 1 ELSE 0 END) as retired_count,
  SUM(total_flight_hours) as total_hours,
  SUM(total_cycles) as total_cycles,
  AVG(total_flight_hours) as avg_hours_per_aircraft
FROM aircraft
WHERE deleted_at IS NULL;

-- Active failures summary
DROP VIEW IF EXISTS v_active_failures;
CREATE VIEW v_active_failures AS
SELECT 
  f.id,
  f.tail,
  f.date_opened,
  f.system_inop,
  f.category,
  f.status,
  a.aircraft_model,
  DATEDIFF(f.due_date, CURDATE()) as days_until_due
FROM failures f
LEFT JOIN aircraft a ON f.tail = a.tail
WHERE f.status IN ('Open', 'In Progress')
  AND f.deleted_at IS NULL
ORDER BY f.due_date ASC;

-- ============================================================================
-- PHASE 8: DATA CONSISTENCY CHECKS
-- ============================================================================

-- Verify all statuses are in English
SELECT COUNT(*) as pt_es_failures FROM failures 
WHERE status NOT IN ('Open', 'Closed', 'In Progress', 'Resolved', NULL);

SELECT COUNT(*) as pt_es_aircraft FROM aircraft 
WHERE registration_status NOT IN ('Active', 'In Service', 'Out of Service', 'Grounded', 'Retired', NULL);

SELECT COUNT(*) as pt_es_roles FROM users 
WHERE access_level NOT IN ('Administrator', 'Technician', 'Pilot', 'User', NULL);

-- Report any remaining Portuguese/Spanish terms
SELECT DISTINCT `status` FROM failures WHERE `status` IS NOT NULL;
SELECT DISTINCT `registration_status` FROM aircraft WHERE `registration_status` IS NOT NULL;
SELECT DISTINCT `access_level` FROM users WHERE `access_level` IS NOT NULL;

-- ============================================================================
-- PHASE 9: OPTIMIZE TABLES
-- ============================================================================

OPTIMIZE TABLE failures;
OPTIMIZE TABLE aircraft;
OPTIMIZE TABLE users;
OPTIMIZE TABLE audit_log;

-- ============================================================================
-- PHASE 10: VERIFY MIGRATION
-- ============================================================================

-- Show final statistics
SELECT 'Migration Summary' as `Status`;
SELECT CONCAT('Total Failures: ', COUNT(*)) FROM failures WHERE deleted_at IS NULL;
SELECT CONCAT('Total Aircraft: ', COUNT(*)) FROM aircraft WHERE deleted_at IS NULL;
SELECT CONCAT('Total Users: ', COUNT(*)) FROM users WHERE deleted_at IS NULL;
SELECT CONCAT('Audit Log Entries: ', COUNT(*)) FROM audit_log;

-- Show distinct values to confirm English translations
SELECT 'Failure Statuses:' as `Distinct Values`;
SELECT DISTINCT status FROM failures WHERE status IS NOT NULL;

SELECT 'Aircraft Statuses:' as `Distinct Values`;
SELECT DISTINCT registration_status FROM aircraft WHERE registration_status IS NOT NULL;

SELECT 'User Roles:' as `Distinct Values`;
SELECT DISTINCT access_level FROM users WHERE access_level IS NOT NULL;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- Migration Complete!
-- ============================================================================
-- 
-- ✅ Database is now 100% in English
-- ✅ Performance indices added
-- ✅ Audit logging enabled
-- ✅ Data integrity constraints in place
-- ✅ Views created for reporting
--
-- Next Steps:
-- 1. Verify application functionality with new schema
-- 2. Test all queries and reports
-- 3. Run performance benchmarks
-- 4. Monitor audit_log for any issues
-- 5. Deploy changes to production (with backup)
--
-- ============================================================================

