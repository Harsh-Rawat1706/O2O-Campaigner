--
-- PostgreSQL database dump
--

\restrict ajtbDNSaQRcYYhwGahLc0FweSgerFze9O1tVTqKNCcLcgX86gMl8AIbaFJCdNB8

-- Dumped from database version 17.10 (Debian 17.10-1.pgdg13+1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: analytics_event_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.analytics_event_type AS ENUM (
    'impression',
    'view',
    'claim'
);


--
-- Name: offer_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.offer_status AS ENUM (
    'draft',
    'scheduled',
    'active',
    'paused',
    'expired',
    'cancelled'
);


--
-- Name: offer_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.offer_type AS ENUM (
    'percent',
    'fixed'
);


--
-- Name: redemption_source; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.redemption_source AS ENUM (
    'merchant_entered',
    'simulated'
);


--
-- Name: sales_data_source; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.sales_data_source AS ENUM (
    'merchant_entered',
    'simulated_demo'
);


--
-- Name: store_verification_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.store_verification_status AS ENUM (
    'pending',
    'verified',
    'rejected',
    'suspended'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'customer',
    'merchant',
    'admin'
);


--
-- Name: voucher_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.voucher_status AS ENUM (
    'claimed',
    'redeemed',
    'expired',
    'cancelled'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analytics_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analytics_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    store_id uuid NOT NULL,
    offer_id uuid NOT NULL,
    event_type public.analytics_event_type NOT NULL,
    customer_hash character varying(128),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    actor_user_id uuid,
    action character varying(100) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_id uuid,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: campaign_expenses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_expenses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    store_id uuid NOT NULL,
    offer_id uuid,
    amount_paise bigint NOT NULL,
    note text,
    incurred_on date DEFAULT CURRENT_DATE NOT NULL,
    CONSTRAINT campaign_expenses_amount_paise_check CHECK ((amount_paise >= 0))
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    offer_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    body text NOT NULL,
    read_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: offers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.offers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    store_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    type public.offer_type NOT NULL,
    value integer NOT NULL,
    min_order_paise bigint DEFAULT 0 NOT NULL,
    max_discount_paise bigint,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    status public.offer_status DEFAULT 'draft'::public.offer_status NOT NULL,
    max_claims integer,
    per_customer_limit integer DEFAULT 1 NOT NULL,
    terms text,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_fixed_less_than_minimum CHECK (((type <> 'fixed'::public.offer_type) OR (((value)::bigint * 100) < min_order_paise) OR (min_order_paise = 0))),
    CONSTRAINT chk_offer_dates CHECK ((ends_at > starts_at)),
    CONSTRAINT chk_percent_range CHECK (((type <> 'percent'::public.offer_type) OR ((value >= 1) AND (value <= 70)))),
    CONSTRAINT offers_max_claims_check CHECK (((max_claims IS NULL) OR (max_claims > 0))),
    CONSTRAINT offers_max_discount_paise_check CHECK (((max_discount_paise IS NULL) OR (max_discount_paise > 0))),
    CONSTRAINT offers_min_order_paise_check CHECK ((min_order_paise >= 0)),
    CONSTRAINT offers_per_customer_limit_check CHECK ((per_customer_limit > 0)),
    CONSTRAINT offers_value_check CHECK ((value > 0)),
    CONSTRAINT offers_version_check CHECK ((version > 0))
);


--
-- Name: sales_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_transactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    store_id uuid NOT NULL,
    offer_id uuid,
    voucher_id uuid,
    gross_amount_paise bigint NOT NULL,
    discount_paise bigint DEFAULT 0 NOT NULL,
    cogs_paise bigint,
    other_var_cost_paise bigint,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    data_source public.sales_data_source NOT NULL,
    CONSTRAINT sales_transactions_cogs_paise_check CHECK (((cogs_paise IS NULL) OR (cogs_paise >= 0))),
    CONSTRAINT sales_transactions_discount_paise_check CHECK ((discount_paise >= 0)),
    CONSTRAINT sales_transactions_gross_amount_paise_check CHECK ((gross_amount_paise >= 0)),
    CONSTRAINT sales_transactions_other_var_cost_paise_check CHECK (((other_var_cost_paise IS NULL) OR (other_var_cost_paise >= 0)))
);


--
-- Name: store_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.store_categories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL
);


--
-- Name: stores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    owner_user_id uuid NOT NULL,
    category_id uuid,
    name character varying(200) NOT NULL,
    address text NOT NULL,
    lat numeric(9,6) NOT NULL,
    lng numeric(9,6) NOT NULL,
    hours jsonb DEFAULT '{}'::jsonb NOT NULL,
    phone character varying(20),
    verification_status public.store_verification_status DEFAULT 'pending'::public.store_verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT stores_lat_check CHECK (((lat >= ('-90'::integer)::numeric) AND (lat <= (90)::numeric))),
    CONSTRAINT stores_lng_check CHECK (((lng >= ('-180'::integer)::numeric) AND (lng <= (180)::numeric)))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    role public.user_role DEFAULT 'customer'::public.user_role NOT NULL,
    name character varying(150) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    prefs jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: voucher_redemptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voucher_redemptions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    voucher_id uuid NOT NULL,
    store_id uuid NOT NULL,
    redeemed_by uuid NOT NULL,
    bill_amount_paise bigint,
    discount_paise bigint NOT NULL,
    source public.redemption_source NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT voucher_redemptions_bill_amount_paise_check CHECK (((bill_amount_paise IS NULL) OR (bill_amount_paise >= 0))),
    CONSTRAINT voucher_redemptions_discount_paise_check CHECK ((discount_paise >= 0))
);


--
-- Name: vouchers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vouchers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(128) NOT NULL,
    offer_id uuid NOT NULL,
    store_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    status public.voucher_status DEFAULT 'claimed'::public.voucher_status NOT NULL,
    terms_snapshot jsonb NOT NULL,
    claimed_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    redeemed_at timestamp with time zone,
    CONSTRAINT chk_redeemed_timestamp CHECK ((((status = 'redeemed'::public.voucher_status) AND (redeemed_at IS NOT NULL)) OR ((status <> 'redeemed'::public.voucher_status) AND (redeemed_at IS NULL)))),
    CONSTRAINT chk_voucher_expiry CHECK ((expires_at > claimed_at))
);


--
-- Name: analytics_events analytics_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT analytics_events_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: campaign_expenses campaign_expenses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_expenses
    ADD CONSTRAINT campaign_expenses_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: offers offers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.offers
    ADD CONSTRAINT offers_pkey PRIMARY KEY (id);


--
-- Name: sales_transactions sales_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_transactions
    ADD CONSTRAINT sales_transactions_pkey PRIMARY KEY (id);


--
-- Name: store_categories store_categories_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.store_categories
    ADD CONSTRAINT store_categories_name_key UNIQUE (name);


--
-- Name: store_categories store_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.store_categories
    ADD CONSTRAINT store_categories_pkey PRIMARY KEY (id);


--
-- Name: stores stores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT stores_pkey PRIMARY KEY (id);


--
-- Name: notifications uq_notification_user_offer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT uq_notification_user_offer UNIQUE (user_id, offer_id);


--
-- Name: vouchers uq_voucher_offer_customer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vouchers
    ADD CONSTRAINT uq_voucher_offer_customer UNIQUE (offer_id, customer_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: voucher_redemptions voucher_redemptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voucher_redemptions
    ADD CONSTRAINT voucher_redemptions_pkey PRIMARY KEY (id);


--
-- Name: voucher_redemptions voucher_redemptions_voucher_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voucher_redemptions
    ADD CONSTRAINT voucher_redemptions_voucher_id_key UNIQUE (voucher_id);


--
-- Name: vouchers vouchers_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vouchers
    ADD CONSTRAINT vouchers_code_key UNIQUE (code);


--
-- Name: vouchers vouchers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vouchers
    ADD CONSTRAINT vouchers_pkey PRIMARY KEY (id);


--
-- Name: idx_analytics_offer_event_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_offer_event_time ON public.analytics_events USING btree (offer_id, event_type, created_at);


--
-- Name: idx_analytics_store_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_store_time ON public.analytics_events USING btree (store_id, created_at);


--
-- Name: idx_audit_actor_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_actor_time ON public.audit_logs USING btree (actor_user_id, created_at);


--
-- Name: idx_audit_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_entity ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: idx_campaign_expenses_store; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_campaign_expenses_store ON public.campaign_expenses USING btree (store_id);


--
-- Name: idx_notifications_expiry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_expiry ON public.notifications USING btree (expires_at);


--
-- Name: idx_notifications_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_user_created ON public.notifications USING btree (user_id, created_at DESC);


--
-- Name: idx_offers_status_ends; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_offers_status_ends ON public.offers USING btree (status, ends_at);


--
-- Name: idx_offers_store_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_offers_store_status ON public.offers USING btree (store_id, status);


--
-- Name: idx_redemptions_store; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_redemptions_store ON public.voucher_redemptions USING btree (store_id, created_at);


--
-- Name: idx_sales_offer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sales_offer ON public.sales_transactions USING btree (offer_id);


--
-- Name: idx_sales_store_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sales_store_time ON public.sales_transactions USING btree (store_id, occurred_at);


--
-- Name: idx_sales_voucher; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sales_voucher ON public.sales_transactions USING btree (voucher_id);


--
-- Name: idx_stores_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stores_category ON public.stores USING btree (category_id);


--
-- Name: idx_stores_lat_lng; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stores_lat_lng ON public.stores USING btree (lat, lng);


--
-- Name: idx_stores_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stores_owner ON public.stores USING btree (owner_user_id);


--
-- Name: idx_stores_verification; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stores_verification ON public.stores USING btree (verification_status);


--
-- Name: idx_vouchers_customer_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vouchers_customer_status ON public.vouchers USING btree (customer_id, status);


--
-- Name: idx_vouchers_expiry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vouchers_expiry ON public.vouchers USING btree (expires_at);


--
-- Name: idx_vouchers_store_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vouchers_store_status ON public.vouchers USING btree (store_id, status);


--
-- Name: analytics_events analytics_events_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT analytics_events_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.offers(id) ON DELETE RESTRICT;


--
-- Name: analytics_events analytics_events_store_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT analytics_events_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id) ON DELETE RESTRICT;


--
-- Name: audit_logs audit_logs_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: campaign_expenses campaign_expenses_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_expenses
    ADD CONSTRAINT campaign_expenses_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.offers(id) ON DELETE RESTRICT;


--
-- Name: campaign_expenses campaign_expenses_store_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_expenses
    ADD CONSTRAINT campaign_expenses_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id) ON DELETE RESTRICT;


--
-- Name: notifications notifications_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.offers(id) ON DELETE RESTRICT;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: offers offers_store_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.offers
    ADD CONSTRAINT offers_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id) ON DELETE RESTRICT;


--
-- Name: sales_transactions sales_transactions_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_transactions
    ADD CONSTRAINT sales_transactions_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.offers(id) ON DELETE RESTRICT;


--
-- Name: sales_transactions sales_transactions_store_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_transactions
    ADD CONSTRAINT sales_transactions_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id) ON DELETE RESTRICT;


--
-- Name: sales_transactions sales_transactions_voucher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_transactions
    ADD CONSTRAINT sales_transactions_voucher_id_fkey FOREIGN KEY (voucher_id) REFERENCES public.vouchers(id) ON DELETE RESTRICT;


--
-- Name: stores stores_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT stores_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.store_categories(id) ON DELETE RESTRICT;


--
-- Name: stores stores_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT stores_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: voucher_redemptions voucher_redemptions_redeemed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voucher_redemptions
    ADD CONSTRAINT voucher_redemptions_redeemed_by_fkey FOREIGN KEY (redeemed_by) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: voucher_redemptions voucher_redemptions_store_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voucher_redemptions
    ADD CONSTRAINT voucher_redemptions_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id) ON DELETE RESTRICT;


--
-- Name: voucher_redemptions voucher_redemptions_voucher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voucher_redemptions
    ADD CONSTRAINT voucher_redemptions_voucher_id_fkey FOREIGN KEY (voucher_id) REFERENCES public.vouchers(id) ON DELETE RESTRICT;


--
-- Name: vouchers vouchers_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vouchers
    ADD CONSTRAINT vouchers_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: vouchers vouchers_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vouchers
    ADD CONSTRAINT vouchers_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.offers(id) ON DELETE RESTRICT;


--
-- Name: vouchers vouchers_store_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vouchers
    ADD CONSTRAINT vouchers_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict ajtbDNSaQRcYYhwGahLc0FweSgerFze9O1tVTqKNCcLcgX86gMl8AIbaFJCdNB8

