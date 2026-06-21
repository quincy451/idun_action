# DBF1 Database Library

`LIB/DBF1.ACT` documents the current DBF helper names. ACTC recognizes these
names directly, emits imports for the helpers that are actually used, and ALINK
links only the referenced `RT_DBF_*.OBJ` modules into the final PRG.

Current scope:

- one staged DBF file at a time
- read-only header and current-record access, including delete-flag status
- handle `1` for a successfully opened file
- zero return values for inactive handles, invalid fields, invalid records, or
  failed file/REU operations

Helpers:

- `DbfOpen(filename)` stages a DBF file and returns handle `1` on success.
- `DbfClose(handle)` clears the active DBF handle.
- `DbfGo(handle, recno)` moves to a one-based record number and returns success.
- `DbfFieldCount(handle)` returns the number of fields in the staged header.
- `DbfFieldLen(handle, field)` returns the length of a one-based field.
- `DbfReadByte(handle, offset)` returns a raw byte from the current record.
- `DbfDeleted(handle)` returns `1` when the current record's DBF delete flag is
  `*`, otherwise `0`.
- `DbfHeaderLen(handle)` returns the low byte of the staged DBF header length.
- `DbfRecordLen(handle)` returns the low byte of the staged DBF record length.
- `DbfTotalRecs(handle)` returns the low byte of the total record count.
- `DbfCurrRecNo(handle)` returns the low byte of the current record number.

Runtime modules:

- `RT_DBF_STATE.OBJ` stores linked DBF state.
- `RT_DBF_OPEN.OBJ` stages and parses the DBF header.
- `RT_DBF_CLOSE.OBJ` clears the active state.
- `RT_DBF_GO.OBJ` validates and updates the current record.
- `RT_DBF_FIELDCOUNT.OBJ` reads the field count from the header.
- `RT_DBF_FIELDLEN.OBJ` reads one field descriptor length.
- `RT_DBF_READBYTE.OBJ` reads one byte from the current record.
- `RT_DBF_DELETED.OBJ` reads the current record delete flag through
  `RT_DBF_READBYTE.OBJ` and returns boolean status.
- `RT_DBF_HEADERLEN.OBJ` returns the staged DBF header-length low byte.
- `RT_DBF_RECORDLEN.OBJ` returns the staged DBF record-length low byte.
- `RT_DBF_TOTALRECS.OBJ` returns the staged record-count low byte.
- `RT_DBF_CURRRECNO.OBJ` returns the current-record low byte.

The DBF helpers are link-selected. Programs that do not call DBF functions do
not carry DBF helper code in the linked PRG.
