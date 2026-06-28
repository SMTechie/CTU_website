DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS ticket_comments CASCADE;
DROP TABLE IF EXISTS tickets CASCADE;
DROP TABLE IF EXISTS passwords CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS ctu_courses CASCADE;

-- 1. Initialize Extensions First
CREATE EXTENSION IF NOT EXISTS citext;

-- 2. Core Operational Tables
CREATE TABLE users (
    user_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username CITEXT UNIQUE NOT NULL, -- Fixed to use CITEXT cleanly here
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    totp_secret VARCHAR(128) DEFAULT NULL,                         
    account_status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    failed_login_attempts INT DEFAULT 0 NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE passwords (
    password_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    old_password_hash VARCHAR(255) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE tickets (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email CITEXT NOT NULL, -- Fixed to use CITEXT cleanly here
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'New' NOT NULL,
    CONSTRAINT chk_ticket_status CHECK (status IN ('New', 'Assigned', 'In Progress', 'Resolved')), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE ticket_comments (
    comment_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id INT REFERENCES tickets(id) ON DELETE CASCADE NOT NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE audit_logs (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username CITEXT NOT NULL, -- Consistent with users table
    event VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE ctu_courses (
    course_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(150) NOT NULL,
    faculty VARCHAR(100) NOT NULL,
    duration_months INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE applications (
    application_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email CITEXT NOT NULL, -- Consistent case-insensitivity for student emails
    selected_course_id INT REFERENCES ctu_courses(course_id) ON DELETE SET NULL,
    application_status VARCHAR(30) DEFAULT 'Pending Review' NOT NULL,
    CONSTRAINT chk_application_status CHECK (application_status IN ('Pending Review', 'Approved', 'Rejected')), -- Added verification check
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Seed Seed-Data
INSERT INTO users (username, password_hash, mfa_enabled, totp_secret)
VALUES ('admin', '$2b$12$/E23C6HX3Y7IyRxrZk0yTOXSLKg7QDVQoT7omC5240wVbq38LhHzq', true, 'JBSWY3DPEHPK3PXP');

-- 4. High-Performance Indexing Strategy
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_tickets_email ON tickets(email);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_comments_ticket_id ON ticket_comments(ticket_id);
CREATE INDEX idx_applications_course_id ON applications(selected_course_id); -- Added FK Index

-- 5. Automation Layer (Triggers for updated_at)
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;