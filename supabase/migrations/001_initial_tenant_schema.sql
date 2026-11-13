CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    whatsapp_phone_number_id TEXT UNIQUE,
    whatsapp_business_account_id TEXT,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_members (
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'operator', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (business_id, user_id)
);

CREATE TABLE IF NOT EXISTS business_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version > 0),
    display_name TEXT NOT NULL,
    languages TEXT[] NOT NULL DEFAULT ARRAY['English'],
    approved_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT false,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (business_id, version)
);

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    external_customer_id TEXT NOT NULL,
    display_name TEXT,
    phone_hash TEXT,
    consent_status TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (business_id, channel, external_customer_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'handover', 'closed')),
    handover_reason TEXT,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    provider_message_id TEXT,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    message_type TEXT NOT NULL,
    content_reference TEXT,
    language TEXT,
    intent TEXT,
    delivery_status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (business_id, provider_message_id)
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('received', 'processing', 'processed', 'failed')),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    PRIMARY KEY (business_id, provider, external_event_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    actor_user_id UUID,
    event_type TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY business_membership_businesses ON businesses
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = businesses.id
              AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY own_business_membership ON business_members
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY business_membership_profiles ON business_profiles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = business_profiles.business_id
              AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY business_membership_customers ON customers
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = customers.business_id
              AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY business_membership_conversations ON conversations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = conversations.business_id
              AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY business_membership_messages ON messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = messages.business_id
              AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY business_membership_idempotency ON idempotency_keys
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = idempotency_keys.business_id
              AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY business_membership_audit ON audit_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = audit_events.business_id
              AND business_members.user_id = auth.uid()
        )
    );
