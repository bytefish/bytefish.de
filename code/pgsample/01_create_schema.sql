DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'im') THEN

    CREATE SCHEMA im;

END IF;

END;
$$;