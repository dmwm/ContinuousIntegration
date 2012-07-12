#!/usr/bin/env python
"Script to edit sitedb mappings"

from optparse import OptionParser
import sqlite3
import csv
from collections import namedtuple

User = namedtuple('User', 'forename, surname, username, dn')
GroupRole = namedtuple('GroupRole', 'group, role')

class SiteDB:
    def __init__(self, db):
        self.db = sqlite3.connect(db, isolation_level = None).cursor()

    def adduser(self, user, role = None):
        """Add user to db, with optional roles"""
        user_id = self._insert_data('contact', **user._asdict())
        if role.role and role.group:
            group_id = self._insert_data('user_group', name = role.group)
            role_id = self._insert_data('role', title = role.role)
            self._insert_data('group_responsibility', 'contact', contact = user_id,
                                    user_group = group_id, role = role_id)


    def _insert_data(self, table, returning = 'id', **kwargs):
        """Insert given data to db
        Use with trusted sources of input data only.
        """
        if not kwargs:
            raise ValueError, 'no data to insert to %s' % table
        query = " AND ".join(['%s="%s"' % (key, kwargs[key]) for key in kwargs])
        data = self.db.execute('SELECT DISTINCT %(returning)s FROM %(table)s WHERE %(query)s' % locals()).fetchone()
        # key, value order may not be the same...
        fields = ", ".join(kwargs)
        values = "?, ".join(['' for _ in range(len(kwargs) + 1)])
        values = values.rstrip(', ')
        if not data:
            #to_insert = ", ".join(['%s="%s"' % (key, kwargs[key]) for key in kwargs])
            to_insert = 'INSERT INTO %(table)s (%(fields)s) VALUES (%(values)s)' % locals()
            self.db.execute(to_insert, kwargs.values())
            data = self.db.execute('SELECT DISTINCT %(returning)s FROM %(table)s WHERE %(query)s' % locals()).fetchone()
        if not data:
            raise RuntimeError, "Can't get inserted row"
        return data[0]

def main():
    usage = "usage: %prog [options] db"
    parser = OptionParser(usage = usage)
    parser.add_option("-m", "--mapping-file", dest="mapping_file",
                      help="Mapping file", metavar="FILE")
    (options, args) = parser.parse_args()
    if not args:
        parser.error('SiteDB db file not provided')
    db = args[0]

    mysitedb = SiteDB(db)

    if options.mapping_file:
        with open(options.mapping_file, 'rb') as mapping:
            reader = csv.reader(mapping)
            for row in reader:
                if not row or row[0].startswith('#'):
                    continue
                thisuser = User(*row[:-2])
                thisrole = GroupRole(*row[-2:])
                mysitedb.adduser(thisuser, thisrole)


if __name__ == '__main__':
    main()
