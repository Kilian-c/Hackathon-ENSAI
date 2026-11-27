-- Partage des expériences importées (P1, cahier section 2.6 et annexe C).
-- À coller une fois dans l'éditeur SQL du projet Supabase (SQL Editor, New query, Run).
--
-- Règles : insertion anonyme ; une ligne enregistrée ne change plus jamais (ni modification ni
-- suppression) ; lecture seulement par identifiant, via la fonction get_shared_experiment : la table
-- elle-même n'est pas lisible, donc personne ne peut lister les expériences des autres.

create table if not exists public.shared_experiments (
  id             text primary key check (id ~ '^[A-Za-z0-9_-]{10,32}$'),
  schema_version integer not null check (schema_version = 1),
  content        text not null check (octet_length(content) <= 65536),
  content_hash   text not null check (content_hash ~ '^[0-9a-f]{64}$'),
  created_at     timestamptz not null default now()
);

alter table public.shared_experiments enable row level security;

-- Insertion anonyme (clé « anon » de l'interface). Aucune politique select, update ni delete.
drop policy if exists "insertion anonyme" on public.shared_experiments;
create policy "insertion anonyme" on public.shared_experiments
  for insert to anon, authenticated
  with check (true);

revoke update, delete, truncate on public.shared_experiments from anon, authenticated;

-- Lecture par identifiant : POST /rest/v1/rpc/get_shared_experiment {"p_id": "..."}
create or replace function public.get_shared_experiment(p_id text)
returns table (id text, schema_version integer, content text, content_hash text, created_at timestamptz)
language sql
stable
security definer
set search_path = public
as $$
  select s.id, s.schema_version, s.content, s.content_hash, s.created_at
  from public.shared_experiments s
  where s.id = p_id
$$;

revoke all on function public.get_shared_experiment(text) from public;
grant execute on function public.get_shared_experiment(text) to anon, authenticated;
