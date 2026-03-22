"""
PostgreSQL dump -> MySQL import (final version)
"""
import re
import subprocess

PG_DUMP  = r"c:\med final\smart-medicvista-erp\pharmamgmt\backups\backup_20251220_181030.sql"
MYSQL_OUT= r"c:\med final\smart-medicvista-erp\pharmamgmt\backups\mysql_import.sql"
MYSQL    = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
DB, USER, PWD = "pharma_db", "root", "Pratik@123"

SKIP = {
    "django_migrations", "django_content_type", "auth_permission",
    "auth_group", "auth_group_permissions", "auth_user_groups",
    "auth_user_user_permissions", "django_admin_log", "django_session",
    "inventory_calculation",
}

DROP_COLS = {
    "core_productmaster": {
        "cached_total_stock", "cached_avg_mrp", "cached_stock_value",
        "cached_batch_count", "cache_updated_at"
    },
}


def tokenize_pg(s):
    """
    Tokenize a PostgreSQL VALUES string into a list of raw value strings.
    Handles: 'string with \\'s and \\' escapes', NULL, numbers, true, false
    """
    tokens, cur, in_str = [], [], False
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            if c == '\\':                    # PG escape char
                cur.append(c)
                if i + 1 < len(s):
                    cur.append(s[i+1])
                    i += 2
                else:
                    i += 1
                continue
            elif c == "'":
                cur.append(c)
                in_str = False
            else:
                cur.append(c)
        else:
            if c == "'":
                in_str = True
                cur.append(c)
            elif c == ',':
                tokens.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(c)
        i += 1
    if cur:
        tokens.append(''.join(cur).strip())
    return tokens


def pg_val_to_mysql(v):
    """Convert a single PostgreSQL value token to MySQL-compatible string."""
    v = v.strip()
    if v.lower() == 'true':
        return '1'
    if v.lower() == 'false':
        return '0'
    if v.startswith("'") and v.endswith("'"):
        inner = v[1:-1]
        inner = inner.replace("\\'", "''")   # PG \' -> MySQL ''
        return f"'{inner}'"
    return v


def convert_line(line):
    """
    Convert one PostgreSQL INSERT line to MySQL INSERT.
    Returns (table, sql) or (table, None) if skipped.
    """
    line = line.strip()
    if not line.startswith("INSERT INTO"):
        return None, None

    # Remove public. schema prefix
    line = re.sub(r"^INSERT INTO public\.", "INSERT INTO ", line)

    # Extract table name
    m = re.match(r"INSERT INTO \"?(\w+)\"?\s+\(", line)
    if not m:
        return None, None
    table = m.group(1)

    if table in SKIP:
        return table, None

    # Parse: INSERT INTO table (col1,col2,...) VALUES (v1,v2,...);
    # Find columns section
    col_start = line.index('(') + 1
    col_end   = line.index(')', col_start)
    cols = [c.strip() for c in line[col_start:col_end].split(',')]

    # Find VALUES ( ... ) - scan from after VALUES keyword
    val_kw = line.index('VALUES', col_end) + len('VALUES')
    # skip whitespace then (
    i = val_kw
    while i < len(line) and line[i] in (' ', '\t'):
        i += 1
    assert line[i] == '(', f"Expected ( after VALUES, got: {line[i]!r}"
    val_start = i + 1

    # Find matching closing ) - scan respecting strings
    depth, in_str, j = 0, False, val_start
    while j < len(line):
        c = line[j]
        if in_str:
            if c == '\\':
                j += 2; continue
            if c == "'":
                in_str = False
        else:
            if c == "'":
                in_str = True
            elif c == '(':
                depth += 1
            elif c == ')':
                if depth == 0:
                    break
                depth -= 1
        j += 1
    vals_str = line[val_start:j]
    vals = tokenize_pg(vals_str)

    if len(cols) != len(vals):
        # fallback: basic conversion, no column stripping
        sql = line.rstrip(';')
        sql = re.sub(r"^INSERT INTO (\w+)", r"INSERT INTO `\1`", sql)
        return table, sql

    # Strip unwanted columns
    drop = DROP_COLS.get(table, set())
    pairs = [(c, v) for c, v in zip(cols, vals) if c not in drop]
    cols = [p[0] for p in pairs]
    vals = [p[1] for p in pairs]

    # Convert values
    vals = [pg_val_to_mysql(v) for v in vals]

    cols_sql = ', '.join(f'`{c}`' for c in cols)
    vals_sql = ', '.join(vals)
    return table, f"INSERT INTO `{table}` ({cols_sql}) VALUES ({vals_sql})"


def main():
    print("Reading PostgreSQL dump...")
    with open(PG_DUMP, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    print(f"Total lines: {len(lines)}")

    inserts, counts, skipped = [], {}, {}

    for lineno, line in enumerate(lines, 1):
        line = line.rstrip('\r\n')
        if not line.startswith("INSERT INTO"):
            continue
        try:
            table, sql = convert_line(line)
        except Exception as e:
            print(f"  PARSE ERROR line {lineno}: {e} | {line[:80]}")
            continue
        if table is None:
            continue
        if sql is None:
            skipped[table] = skipped.get(table, 0) + 1
            continue
        inserts.append(sql)
        counts[table] = counts.get(table, 0) + 1

    print("\nTables to import:")
    for t, c in sorted(counts.items()):
        print(f"  {t}: {c} rows")
    print("\nSkipped:")
    for t, c in sorted(skipped.items()):
        print(f"  {t}: {c} rows")

    tables_order = list(dict.fromkeys(
        re.match(r"INSERT INTO `([^`]+)`", s).group(1) for s in inserts
    ))

    print(f"\nWriting {len(inserts)} statements...")
    with open(MYSQL_OUT, 'w', encoding='utf-8') as f:
        f.write("SET FOREIGN_KEY_CHECKS=0;\n")
        f.write("SET sql_mode='';\n")
        f.write("SET NAMES utf8mb4;\n\n")
        for t in tables_order:
            f.write(f"TRUNCATE TABLE `{t}`;\n")
        f.write("\n")
        for s in inserts:
            f.write(s + ";\n")
        f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")

    print("Importing into MySQL...")
    with open(MYSQL_OUT, 'r', encoding='utf-8') as f:
        sql_data = f.read()

    r = subprocess.run(
        [MYSQL, f"-u{USER}", f"-p{PWD}", DB],
        input=sql_data, capture_output=True, text=True, encoding='utf-8'
    )

    if r.returncode == 0:
        print("\nImport SUCCESS!")
    else:
        print("\nImport FAILED:")
        print(r.stderr[:3000])

    print("\nFinal row counts (PG expected -> MySQL actual):")
    all_ok = True
    for t in sorted(counts.keys()):
        r2 = subprocess.run(
            [MYSQL, f"-u{USER}", f"-p{PWD}", DB, "-e", f"SELECT COUNT(*) FROM `{t}`;"],
            capture_output=True, text=True
        )
        cnt = r2.stdout.strip().split('\n')[-1] if r2.stdout else "ERR"
        pg_cnt = counts[t]
        ok = str(cnt) == str(pg_cnt)
        status = "OK" if ok else f"MISMATCH (expected {pg_cnt})"
        if not ok:
            all_ok = False
        print(f"  [{status}] {t}: {cnt}")

    if all_ok:
        print("\nAll tables match!")
    else:
        print("\nSome tables have mismatches - check errors above.")


if __name__ == "__main__":
    main()
