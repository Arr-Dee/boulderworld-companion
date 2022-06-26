import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL)

# Open a cursor to perform database operations
cur = conn.cursor()

# Execute a command: this creates a new table
cur.execute('DROP TABLE IF EXISTS users;')
cur.execute('CREATE TABLE users (id serial PRIMARY KEY NOT NULL,'
                                 'username TEXT NOT NULL,'
                                 'hash TEXT NOT NULL)'
                                 'leaderboard BOOLEAN NOT NULL;'
                                 )

# Execute a command: this creates a new table
cur.execute('DROP TABLE IF EXISTS results;')
cur.execute('CREATE TABLE results (id serial PRIMARY KEY NOT NULL,'
                                 'user_id INTEGER NOT NULL,'
                                 'comp TEXT NOT NULL,'
                                 'results TEXT NOT NULL);'
                                 )

# Execute a command: this creates a new table
cur.execute('DROP TABLE IF EXISTS comps;')
cur.execute('CREATE TABLE comps (id serial PRIMARY KEY NOT NULL,'
                                 'comp TEXT NOT NULL,'
                                 'name TEXT NOT NULL,'
                                 'climbs INTEGER NOT NULL,'
                                 'zone INTEGER NOT NULL,'
                                 'top INTEGER NOT NULL);'
                                 )


# Insert data into the table

cur.execute('INSERT INTO comps (comp, name, climbs, zone, top)'
            'VALUES (%s, %s, %s, %s, %s)', ('feb22', 'Feb 2022', 60, 6, 10))

cur.execute('INSERT INTO comps (comp, name, climbs, zone, top)'
            'VALUES (%s, %s, %s, %s, %s)', ('mar22', 'Mar 2022', 20, 6, 10))

cur.execute('INSERT INTO comps (comp, name, climbs, zone, top)'
            'VALUES (%s, %s, %s, %s, %s)', ('apr22', 'Apr 2022', 60, 6, 10))


conn.commit()

cur.close()
conn.close()