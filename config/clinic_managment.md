-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.audit_logs (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  clinic_id uuid,
  user_id uuid,
  action text,
  entity_type text,
  entity_id uuid,
  timestamp timestamp without time zone DEFAULT now(),
  CONSTRAINT audit_logs_pkey PRIMARY KEY (id),
  CONSTRAINT audit_logs_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id),
  CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.clinics (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  name text NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT clinics_pkey PRIMARY KEY (id)
);
CREATE TABLE public.consultations (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  visit_id uuid,
  doctor_id uuid,
  symptoms text,
  diagnosis text,
  notes text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT consultations_pkey PRIMARY KEY (id),
  CONSTRAINT consultations_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.visits(id),
  CONSTRAINT consultations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.lab_tests (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  clinic_id uuid,
  name text NOT NULL,
  description text,
  price numeric DEFAULT 0,
  is_active boolean DEFAULT true,
  created_by uuid,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT lab_tests_pkey PRIMARY KEY (id),
  CONSTRAINT lab_tests_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id),
  CONSTRAINT lab_tests_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.profiles(id)
);
CREATE TABLE public.patients (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  clinic_id uuid NOT NULL,
  full_name text NOT NULL,
  gender text,
  date_of_birth date,
  phone text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT patients_pkey PRIMARY KEY (id),
  CONSTRAINT patients_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id)
);
CREATE TABLE public.profiles (
  id uuid NOT NULL,
  clinic_id uuid NOT NULL,
  full_name text,
  role text CHECK (role = ANY (ARRAY['receptionist'::text, 'doctor'::text, 'lab_tech'::text, 'admin'::text])),
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT profiles_pkey PRIMARY KEY (id),
  CONSTRAINT profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id),
  CONSTRAINT profiles_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id)
);
CREATE TABLE public.test_orders (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  visit_id uuid,
  consultation_id uuid,
  test_id uuid,
  status text DEFAULT 'pending'::text CHECK (status = ANY (ARRAY['pending'::text, 'in_progress'::text, 'completed'::text])),
  ordered_by uuid,
  created_at timestamp without time zone DEFAULT now(),
  assigned_to uuid,
  CONSTRAINT test_orders_pkey PRIMARY KEY (id),
  CONSTRAINT test_orders_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.visits(id),
  CONSTRAINT test_orders_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id),
  CONSTRAINT test_orders_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.lab_tests(id),
  CONSTRAINT test_orders_ordered_by_fkey FOREIGN KEY (ordered_by) REFERENCES public.profiles(id),
  CONSTRAINT test_orders_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.profiles(id)
);
CREATE TABLE public.test_results (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  test_order_id uuid,
  technician_id uuid,
  result_data jsonb,
  remarks text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT test_results_pkey PRIMARY KEY (id),
  CONSTRAINT test_results_test_order_id_fkey FOREIGN KEY (test_order_id) REFERENCES public.test_orders(id),
  CONSTRAINT test_results_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.visits (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  clinic_id uuid NOT NULL,
  patient_id uuid,
  created_by uuid,
  status text DEFAULT 'open'::text CHECK (status = ANY (ARRAY['open'::text, 'in_progress'::text, 'completed'::text])),
  created_at timestamp without time zone DEFAULT now(),
  assigned_doctor_id uuid,
  CONSTRAINT visits_pkey PRIMARY KEY (id),
  CONSTRAINT visits_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id),
  CONSTRAINT visits_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id),
  CONSTRAINT visits_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.profiles(id),
  CONSTRAINT visits_assigned_doctor_id_fkey FOREIGN KEY (assigned_doctor_id) REFERENCES public.profiles(id)
);