CREATE DATABASE IF NOT EXISTS bis_compliance;
USE bis_compliance;
CREATE TABLE manufacturers (
    manufacturer_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    registration_number VARCHAR(100),

    country VARCHAR(100) DEFAULT 'India',
    state VARCHAR(100),
    city VARCHAR(100),

    address TEXT,

    email VARCHAR(255),
    phone VARCHAR(30),
    website VARCHAR(500),

    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_manufacturer_registration (registration_number)
);
CREATE TABLE product_categories (
    category_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    parent_category_id BIGINT UNSIGNED NULL,

    category_code VARCHAR(100) NOT NULL,
    category_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_category_code (category_code),

    CONSTRAINT fk_category_parent
        FOREIGN KEY (parent_category_id)
        REFERENCES product_categories(category_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);
CREATE TABLE standards (
    standard_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    standard_number VARCHAR(100) NOT NULL,
    standard_title VARCHAR(500) NOT NULL,

    edition VARCHAR(100),
    publication_date DATE,
    effective_date DATE,

    status ENUM(
        'DRAFT',
        'ACTIVE',
        'SUPERSEDED',
        'WITHDRAWN'
    ) NOT NULL DEFAULT 'ACTIVE',

    issuing_body VARCHAR(255)
        DEFAULT 'Bureau of Indian Standards',

    source_url VARCHAR(1000),

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_standard_number_edition
        (standard_number, edition)
);
CREATE TABLE products (
    product_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    manufacturer_id BIGINT UNSIGNED NOT NULL,
    category_id BIGINT UNSIGNED NOT NULL,

    product_code VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,

    model_number VARCHAR(150),
    description TEXT,

    country_of_origin VARCHAR(100),

    status ENUM(
        'DRAFT',
        'ACTIVE',
        'UNDER_REVIEW',
        'INACTIVE'
    ) NOT NULL DEFAULT 'DRAFT',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_product_code (product_code),

    KEY idx_product_manufacturer (manufacturer_id),
    KEY idx_product_category (category_id),

    CONSTRAINT fk_product_manufacturer
        FOREIGN KEY (manufacturer_id)
        REFERENCES manufacturers(manufacturer_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id)
        REFERENCES product_categories(category_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
CREATE TABLE product_standards (
    product_standard_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    product_id BIGINT UNSIGNED NOT NULL,
    standard_id BIGINT UNSIGNED NOT NULL,

    applicability ENUM(
        'MANDATORY',
        'VOLUNTARY',
        'CONDITIONAL',
        'UNKNOWN'
    ) NOT NULL DEFAULT 'UNKNOWN',

    applicability_reason TEXT,

    effective_from DATE,
    effective_to DATE,

    status ENUM('ACTIVE', 'INACTIVE')
        NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_product_standard
        (product_id, standard_id),

    CONSTRAINT fk_ps_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ps_standard
        FOREIGN KEY (standard_id)
        REFERENCES standards(standard_id)
        ON DELETE RESTRICT
);
CREATE TABLE compliance_requirements (
    requirement_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    standard_id BIGINT UNSIGNED NOT NULL,

    requirement_code VARCHAR(100) NOT NULL,
    requirement_title VARCHAR(255) NOT NULL,

    requirement_description TEXT,

    requirement_type ENUM(
        'DOCUMENT',
        'TEST',
        'PROCESS',
        'CERTIFICATION',
        'LABELLING',
        'INSPECTION',
        'OTHER'
    ) NOT NULL,

    mandatory BOOLEAN NOT NULL DEFAULT TRUE,

    sequence_no INT UNSIGNED DEFAULT 0,

    source_reference VARCHAR(500),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_requirement_code_standard
        (standard_id, requirement_code),

    CONSTRAINT fk_requirement_standard
        FOREIGN KEY (standard_id)
        REFERENCES standards(standard_id)
        ON DELETE CASCADE
);
CREATE TABLE documents (
    document_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    document_type ENUM(
        'TECHNICAL_SPECIFICATION',
        'TEST_REPORT',
        'CERTIFICATE',
        'DECLARATION',
        'APPLICATION',
        'LICENSE',
        'MANUAL',
        'OTHER'
    ) NOT NULL,

    document_name VARCHAR(255) NOT NULL,

    file_name VARCHAR(255),
    mime_type VARCHAR(100),

    storage_url VARCHAR(1000),

    document_number VARCHAR(150),

    issue_date DATE,
    expiry_date DATE,

    verification_status ENUM(
        'PENDING',
        'VERIFIED',
        'REJECTED',
        'EXPIRED'
    ) NOT NULL DEFAULT 'PENDING',

    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE product_requirements (
    product_requirement_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    product_id BIGINT UNSIGNED NOT NULL,
    requirement_id BIGINT UNSIGNED NOT NULL,

    status ENUM(
        'NOT_STARTED',
        'IN_PROGRESS',
        'COMPLETED',
        'FAILED',
        'NOT_APPLICABLE'
    ) NOT NULL DEFAULT 'NOT_STARTED',

    evidence_document_id BIGINT UNSIGNED NULL,

    due_date DATE,

    completed_at DATETIME NULL,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_product_requirement
        (product_id, requirement_id),

    CONSTRAINT fk_pr_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_pr_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES compliance_requirements(requirement_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_pr_evidence_document
        FOREIGN KEY (evidence_document_id)
        REFERENCES documents(document_id)
        ON DELETE SET NULL
);
CREATE TABLE product_documents (
    product_document_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    product_id BIGINT UNSIGNED NOT NULL,
    document_id BIGINT UNSIGNED NOT NULL,

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_product_document
        (product_id, document_id),

    CONSTRAINT fk_pd_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_pd_document
        FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE
);
CREATE TABLE tests (
    test_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    product_id BIGINT UNSIGNED NOT NULL,
    requirement_id BIGINT UNSIGNED NULL,

    test_name VARCHAR(255) NOT NULL,

    laboratory_name VARCHAR(255),

    test_reference_number VARCHAR(150),

    test_date DATE,
    report_date DATE,

    result ENUM(
        'PENDING',
        'PASS',
        'FAIL',
        'INCONCLUSIVE'
    ) NOT NULL DEFAULT 'PENDING',

    report_document_id BIGINT UNSIGNED NULL,

    remarks TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_test_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_test_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES compliance_requirements(requirement_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_test_document
        FOREIGN KEY (report_document_id)
        REFERENCES documents(document_id)
        ON DELETE SET NULL
);
CREATE TABLE certifications (
    certification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    product_id BIGINT UNSIGNED NOT NULL,

    certification_type VARCHAR(100) NOT NULL,

    certificate_number VARCHAR(150),

    issuing_authority VARCHAR(255),

    issue_date DATE,
    expiry_date DATE,

    status ENUM(
        'PENDING',
        'ACTIVE',
        'EXPIRED',
        'SUSPENDED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'PENDING',

    certificate_document_id BIGINT UNSIGNED NULL,

    remarks TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_cert_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_cert_document
        FOREIGN KEY (certificate_document_id)
        REFERENCES documents(document_id)
        ON DELETE SET NULL
);
CREATE TABLE compliance_alerts (
    alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    product_id BIGINT UNSIGNED NOT NULL,

    requirement_id BIGINT UNSIGNED NULL,

    alert_type ENUM(
        'MISSING_REQUIREMENT',
        'OVERDUE_REQUIREMENT',
        'FAILED_TEST',
        'EXPIRING_CERTIFICATION',
        'EXPIRED_DOCUMENT',
        'STANDARD_UPDATE',
        'GENERAL'
    ) NOT NULL,

    severity ENUM(
        'LOW',
        'MEDIUM',
        'HIGH',
        'CRITICAL'
    ) NOT NULL DEFAULT 'MEDIUM',

    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    status ENUM(
        'OPEN',
        'ACKNOWLEDGED',
        'RESOLVED',
        'DISMISSED'
    ) NOT NULL DEFAULT 'OPEN',

    due_date DATE NULL,
    resolved_at DATETIME NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_alert_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_alert_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES compliance_requirements(requirement_id)
        ON DELETE SET NULL
);
INSERT INTO manufacturers (
    name,
    legal_name,
    registration_number,
    country,
    state,
    city,
    email
)
VALUES (
    'Demo Electronics Pvt Ltd',
    'Demo Electronics Private Limited',
    'DEMO-MFG-001',
    'India',
    'Delhi',
    'New Delhi',
    'demo@example.com'
);
SELECT * FROM manufacturers;
INSERT INTO product_categories
(category_code, category_name, description)
VALUES
(
    'ELEC',
    'Electrical and Electronic Products',
    'Demo main category'
),
(
    'HOME',
    'Home Appliances',
    'Demo category'
);
SELECT * FROM product_categories;
INSERT INTO standards (
    standard_number,
    standard_title,
    edition,
    publication_date,
    effective_date,
    status,
    issuing_body,
    description
)
VALUES (
    'DEMO-IS-1001',
    'Demo Standard for Electronic Product',
    'Demo Edition 2026',
    '2026-01-01',
    '2026-01-01',
    'ACTIVE',
    'DEMO DATA ONLY',
    'Synthetic standard for testing the database'
);
INSERT INTO products (
    manufacturer_id,
    category_id,
    product_code,
    product_name,
    model_number,
    description,
    country_of_origin,
    status
)
VALUES (
    1,
    1,
    'DEMO-TV-001',
    'Demo Smart Television',
    'DSTV-55-A1',
    'Demo product for testing',
    'India',
    'ACTIVE'
);
INSERT INTO product_standards (
    product_id,
    standard_id,
    applicability,
    applicability_reason
)
VALUES (
    1,
    1,
    'MANDATORY',
    'DEMO applicability for project testing'
);
SELECT
    p.product_name,
    s.standard_number,
    s.standard_title,
    ps.applicability
FROM product_standards ps
JOIN products p
    ON ps.product_id = p.product_id
JOIN standards s
    ON ps.standard_id = s.standard_id;
    INSERT INTO compliance_requirements (
    standard_id,
    requirement_code,
    requirement_title,
    requirement_description,
    requirement_type,
    mandatory,
    sequence_no
)
VALUES
(
    1,
    'DEMO-R001',
    'Technical Documentation',
    'Demo requirement for technical documentation',
    'DOCUMENT',
    TRUE,
    1
),
(
    1,
    'DEMO-R002',
    'Product Testing',
    'Demo requirement for product testing',
    'TEST',
    TRUE,
    2
),
(
    1,
    'DEMO-R003',
    'Certification Evidence',
    'Demo requirement for certification evidence',
    'CERTIFICATION',
    TRUE,
    3
);
INSERT INTO product_requirements (
    product_id,
    requirement_id,
    status,
    notes
)
VALUES
(
    1,
    1,
    'COMPLETED',
    'Demo documentation completed'
),
(
    1,
    2,
    'IN_PROGRESS',
    'Demo testing in progress'
),
(
    1,
    3,
    'NOT_STARTED',
    'Demo certification pending'
);
SELECT
    p.product_name,
    cr.requirement_title,
    pr.status
FROM product_requirements pr
JOIN products p
    ON pr.product_id = p.product_id
JOIN compliance_requirements cr
    ON pr.requirement_id = cr.requirement_id;
    SELECT
    p.product_id,
    p.product_name,

    COUNT(pr.product_requirement_id)
        AS total_requirements,

    SUM(
        CASE
            WHEN pr.status = 'COMPLETED'
            THEN 1
            ELSE 0
        END
    ) AS completed_requirements,

    ROUND(
        100.0 *
        SUM(
            CASE
                WHEN pr.status = 'COMPLETED'
                THEN 1
                ELSE 0
            END
        )
        /
        COUNT(pr.product_requirement_id),
        2
    ) AS readiness_percentage

FROM products p
LEFT JOIN product_requirements pr
    ON p.product_id = pr.product_id

WHERE p.product_id = 1

GROUP BY
    p.product_id,
    p.product_name;