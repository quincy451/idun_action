/******************************************************************************
 * Minimal DBF API demo in C99
 * NOTE: This is an illustrative example only, not production-ready code!
 *
 * Compile with:  gcc -std=c99 -o dbf_demo dbf_demo.c
 *****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <stdint.h>

/* ---------------------------------------------------------------------------
 * DBF file format notes (simplified):
 *
 *  Offset |  Size | Description
 *  -------+-------+-----------------------------------------
 *    0    |  1    | dBase version (e.g., 0x03 = dBase III)
 *    1    |  3    | Last update (YY MM DD)
 *    4    |  4    | Number of records in file (32-bit, little-endian)
 *    8    |  2    | Position of first data record
 *   10    |  2    | Length of one data record
 *   12    |  20   | Reserved / unused in dBase III
 *   32    | 32*n  | Field descriptors (n fields, each 32 bytes)
 *       ...       | End of field descriptors marker (0x0D)
 *       ...       | Data records
 *
 *  Each data record starts with 1 byte "delete flag" (0x20 = active, 0x2A='*' = deleted)
 *
 *  For simplicity, we will assume only character fields.
 * ------------------------------------------------------------------------- */


/* ---------------------------------------------------------------------------
 * Field definition (simplified)
 * ------------------------------------------------------------------------- */
typedef struct
{
    /* Because the function prototype uses `char field_name[];`
       we will assume a maximum length for demonstration. */
    char field_name[12];  /* dBase typically uses up to 11 chars + terminator */
    int  field_size;
} FIELD_DEF;

/* ---------------------------------------------------------------------------
 * Internal handle for an open DBF file
 * ------------------------------------------------------------------------- */
typedef struct
{
    FILE* fp;           /* File pointer */
    int        total_recs;    /* total active (not deleted) records */
    int        curr_rec;      /* current (active) record index (1-based in many DBF systems) */
    int        record_count;  /* total records in file (including deleted) */
    int        header_size;   /* offset to first record */
    int        record_size;   /* length of one record (including delete flag) */
    int        field_count;
    FIELD_DEF* fields;        /* array of field definitions */
    /* Additional DBF metadata can go here */
} DBF_HANDLE;

/* ---------------------------------------------------------------------------
 * We'll keep a simple global array of pointers to DBF_HANDLE for
 * demonstration. A real implementation might manage these differently.
 * ------------------------------------------------------------------------- */
#define MAX_DBF_HANDLES  16
static DBF_HANDLE* g_dbf_handles[MAX_DBF_HANDLES] = { NULL };

/* ---------------------------------------------------------------------------
 * Helper: find a free slot for storing DBF_HANDLE
 * ------------------------------------------------------------------------- */
static int find_free_handle_slot(void)
{
    for (int i = 0; i < MAX_DBF_HANDLES; i++)
    {
        if (g_dbf_handles[i] == NULL)
            return i;
    }
    return -1; /* no free slot */
}

/* ---------------------------------------------------------------------------
 * Helper: read_le32, read_le16 for little-endian
 * ------------------------------------------------------------------------- */
static uint32_t read_le32(const unsigned char* buf)
{
    return (uint32_t)(buf[0]) |
           (uint32_t)(buf[1]) << 8 |
           (uint32_t)(buf[2]) << 16 |
           (uint32_t)(buf[3]) << 24;
}

static uint16_t read_le16(const unsigned char* buf)
{
    return (uint16_t)(buf[0]) |
           (uint16_t)(buf[1]) << 8;
}

/* ---------------------------------------------------------------------------
 * Little-endian helper for writing a 2-byte and 4-byte integer
 * ------------------------------------------------------------------------- */
static void write_le16(uint16_t value, FILE* fp)
{
    unsigned char buf[2];
    buf[0] = (unsigned char)(value & 0xFF);
    buf[1] = (unsigned char)((value >> 8) & 0xFF);
    fwrite(buf, 1, 2, fp);
}
static void write_le32(uint32_t value, FILE* fp)
{
    unsigned char buf[4];
    buf[0] = (unsigned char)(value & 0xFF);
    buf[1] = (unsigned char)((value >> 8) & 0xFF);
    buf[2] = (unsigned char)((value >> 16) & 0xFF);
    buf[3] = (unsigned char)((value >> 24) & 0xFF);
    fwrite(buf, 1, 4, fp);
}

/* ---------------------------------------------------------------------------
 * PROTOTYPES of existing functions (so we can place dbf_creat anywhere).
 * ------------------------------------------------------------------------- */
int dbf_open(char* filename, int* field_count, FIELD_DEF* fielddefs[]);
int dbf_currrecno(int handle);
int dbf_total_recs(int handle);
bool dbf_read(int handle, char* fields[]);
bool dbf_delrec(int handle);
bool dbf_delrecat(int handle, int recno);
bool dbf_write(int handle, char* fields[]);
void dbf_close(int handle);
bool dbf_compress(char* filename);
int dbf_creat(const char* filename, int field_count, FIELD_DEF* fielddefs);



/* ---------------------------------------------------------------------------
 * dbf_open
 *   - Open a DBF file, read header info, fill in fielddefs, etc.
 *   - Return an int "handle" or -1 on failure.
 *   - Also store number of fields in *field_count and fill fielddefs[] array.
 * ------------------------------------------------------------------------- */
int dbf_open(char* filename, int* field_count, FIELD_DEF* fielddefs[])
{
    FILE* fp = fopen(filename, "rb+");
    if (!fp)
    {
        fprintf(stderr, "Failed to open %s\n", filename);
        return -1;
    }

    /* Allocate a DBF_HANDLE structure */
    DBF_HANDLE* h = (DBF_HANDLE*)calloc(1, sizeof(DBF_HANDLE));
    if (!h)
    {
        fclose(fp);
        return -1;
    }

    /* Read header (32 bytes minimum) */
    unsigned char header[32];
    if (fread(header, 1, 32, fp) != 32)
    {
        fclose(fp);
        free(h);
        return -1;
    }

    /* Parse number of records, header size, record size from header */
    h->record_count = (int)read_le32(&header[4]);  /* # of records in file */
    h->header_size = (int)read_le16(&header[8]);  /* position of first data record */
    h->record_size = (int)read_le16(&header[10]); /* length of each data record */

    /* Move file pointer to start of field descriptors (32 bytes read so far) */
    int fieldDescCount = 0;
    /* Each field descriptor is 32 bytes, ends with 0x0D */
    /* The total field descriptors area ends at h->header_size - 1. */
    long currentPos = 32;
    fseek(fp, 32, SEEK_SET);

    /* We will read fields until we see 0x0D or we reach h->header_size - 1 */
    {
        unsigned char fieldDesc[32];
        while (1)
        {
            if (fread(fieldDesc, 1, 32, fp) != 32)
                break; /* read error or end of file */

            if (fieldDesc[0] == 0x0D)
            {
                /* end of field descriptors */
                break;
            }

            /* Fill in field definition from the 32-byte descriptor. In the real
               DBF spec, offset 11 is the field type, offset 16 is field length, etc. */
            FIELD_DEF def;
            memset(&def, 0, sizeof(def));
            /* copy up to 11 chars for the field name */
            strncpy(def.field_name, (char*)fieldDesc, 11);
            def.field_name[11] = '\0';  /* ensure null termination */
            /* field length is at offset 16 in the descriptor */
            def.field_size = (int)fieldDesc[16];

            /* Append to a dynamic array or a fixed array. For simplicity, we will
               just re-alloc a small array each time. */
            if (fieldDescCount == 0)
                h->fields = (FIELD_DEF*)malloc(sizeof(FIELD_DEF));
            else
                h->fields = (FIELD_DEF*)realloc(h->fields, (fieldDescCount + 1) * sizeof(FIELD_DEF));

            h->fields[fieldDescCount] = def;
            fieldDescCount++;
        }
    }

    h->field_count = fieldDescCount;
    h->fp = fp;

    /* Calculate how many are actually *active* (not deleted).
       We will just assume for now that we need to iterate the file to find out. */
    int activeCount = 0;
    {
        /* Save current file pos */
        long savePos = ftell(fp);
        /* Move to first data record */
        fseek(fp, h->header_size, SEEK_SET);

        for (int i = 0; i < h->record_count; i++)
        {
            char deleteFlag;
            if (fread(&deleteFlag, 1, 1, fp) != 1)
                break; /* can't read further */

            if (deleteFlag != '*')  /* '*' = deleted */
                activeCount++;

            /* skip the rest of the record */
            fseek(fp, h->record_size - 1, SEEK_CUR);
        }

        /* restore position */
        fseek(fp, savePos, SEEK_SET);
    }
    h->total_recs = activeCount;
    h->curr_rec = (activeCount > 0) ? 1 : 0; /* start at first active record if any */

    /* Return data to caller */
    *field_count = fieldDescCount;
    *fielddefs = h->fields;

    /* Find a free slot to store this handle */
    int handle_id = find_free_handle_slot();
    if (handle_id < 0)
    {
        fprintf(stderr, "No free DBF handle slots\n");
        fclose(fp);
        free(h->fields);
        free(h);
        return -1;
    }

    g_dbf_handles[handle_id] = h;
    return handle_id;
}

/* ---------------------------------------------------------------------------
 * dbf_currrecno
 *   - Return the current (active) record number in 1-based indexing
 * ------------------------------------------------------------------------- */
int dbf_currrecno(int handle)
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return -1;

    return g_dbf_handles[handle]->curr_rec;
}

/* ---------------------------------------------------------------------------
 * dbf_total_recs
 *   - Return total *active* records in the DBF
 * ------------------------------------------------------------------------- */
int dbf_total_recs(int handle)
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return -1;

    return g_dbf_handles[handle]->total_recs;
}

/* ---------------------------------------------------------------------------
 * Internal helper: move file pointer to the start of the nth record (1-based),
 * ignoring deleted vs. not. We will literally do (n-1)*record_size from
 * h->header_size. Then we read the delete flag to see if it is deleted or not.
 *
 * For a real DBF, you'd typically keep a separate "active record index" or
 * iterate through the file. This function just positions the file pointer.
 * ------------------------------------------------------------------------- */
static bool goto_record(DBF_HANDLE* h, int nth)
{
    if (nth < 1 || nth > h->record_count)
        return false;

    long offset = h->header_size + (long)(nth - 1) * h->record_size;
    if (fseek(h->fp, offset, SEEK_SET) != 0)
        return false;
    return true;
}

/* ---------------------------------------------------------------------------
 * dbf_read
 *   - Read the fields of the "current active" record into the provided fields[].
 *   - fields[] must have enough space to hold string data for each field.
 *   - This minimal version reads only character fields.
 * ------------------------------------------------------------------------- */
bool dbf_read(int handle, char* fields[])
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return false;

    DBF_HANDLE* h = g_dbf_handles[handle];
    if (h->curr_rec < 1 || h->curr_rec > h->record_count || h->total_recs == 0)
        return false;

    /* We need to find the nth active record. In a minimal approach, we’ll
       scan from the start to find the h->curr_rec-th *active* record. */
    int active_found = 0;
    for (int r = 1; r <= h->record_count; r++)
    {
        if (!goto_record(h, r))
            return false;

        char deleteFlag = 0;
        if (fread(&deleteFlag, 1, 1, h->fp) != 1)
            return false;

        if (deleteFlag != '*') /* not deleted */
        {
            active_found++;
            if (active_found == h->curr_rec)
            {
                /* now read the fields */
                for (int f = 0; f < h->field_count; f++)
                {
                    int size = h->fields[f].field_size;
                    if (fread(fields[f], 1, size, h->fp) != (size_t)size)
                        return false;
                    fields[f][size] = '\0'; /* null-terminate for safety */

                    /* skip to next field position if needed, but in this simplified
                       example, we assume the record exactly matches. */
                }
                return true;
            }
        }
    }

    return false; /* not found or some error */
}

/* ---------------------------------------------------------------------------
 * dbf_delrec
 *   - Mark the *current active record* as deleted ('*'), then move to the next
 *     active record if possible.
 * ------------------------------------------------------------------------- */
bool dbf_delrec(int handle)
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return false;

    DBF_HANDLE* h = g_dbf_handles[handle];
    if (h->curr_rec < 1 || h->curr_rec > h->record_count || h->total_recs == 0)
        return false;

    /* We want the h->curr_rec-th active record physically in the file. */
    int active_found = 0;
    for (int r = 1; r <= h->record_count; r++)
    {
        if (!goto_record(h, r))
            return false;

        char deleteFlag = 0;
        if (fread(&deleteFlag, 1, 1, h->fp) != 1)
            return false;

        if (deleteFlag != '*')
        {
            active_found++;
            if (active_found == h->curr_rec)
            {
                /* Mark this record as deleted */
                fseek(h->fp, -1, SEEK_CUR);
                fputc('*', h->fp);
                fflush(h->fp);

                h->total_recs--;
                /* Move current record pointer to the next active record if possible */
                if (h->curr_rec > h->total_recs)
                    h->curr_rec = h->total_recs; /* clamp */
                return true;
            }
        }
    }

    return false;
}

/* ---------------------------------------------------------------------------
 * dbf_delrecat
 *   - Mark the record number (active numbering) supplied as deleted.
 *   - If recno == current record, we also move on by one.
 * ------------------------------------------------------------------------- */
bool dbf_delrecat(int handle, int recno)
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return false;

    DBF_HANDLE* h = g_dbf_handles[handle];
    if (recno < 1 || recno > h->total_recs)
        return false;

    /* Find the recno-th active record physically in the file. */
    int active_found = 0;
    for (int r = 1; r <= h->record_count; r++)
    {
        if (!goto_record(h, r))
            return false;

        char deleteFlag = 0;
        if (fread(&deleteFlag, 1, 1, h->fp) != 1)
            return false;

        if (deleteFlag != '*')
        {
            active_found++;
            if (active_found == recno)
            {
                /* Mark this record as deleted */
                fseek(h->fp, -1, SEEK_CUR);
                fputc('*', h->fp);
                fflush(h->fp);

                h->total_recs--;
                /* If recno == current record, move current record pointer */
                if (recno == h->curr_rec)
                {
                    if (h->curr_rec > h->total_recs)
                        h->curr_rec = h->total_recs;
                }
                return true;
            }
        }
    }

    return false;
}

/* ---------------------------------------------------------------------------
 * dbf_write
 *   - Write the fields[] to the *current active* record.
 *   - For simplicity, we assume the record sizes match exactly.
 * ------------------------------------------------------------------------- */
bool dbf_write(int handle, char* fields[])
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return false;

    DBF_HANDLE* h = g_dbf_handles[handle];
    if (h->curr_rec < 1 || h->curr_rec > h->record_count || h->total_recs == 0)
        return false;

    /* Find the h->curr_rec-th active record physically. */
    int active_found = 0;
    for (int r = 1; r <= h->record_count; r++)
    {
        if (!goto_record(h, r))
            return false;

        char deleteFlag = 0;
        if (fread(&deleteFlag, 1, 1, h->fp) != 1)
            return false;

        if (deleteFlag != '*')
        {
            active_found++;
            if (active_found == h->curr_rec)
            {
                /* Overwrite from this point on. We just wrote 1 byte reading above,
                   so go back 1 byte, write space for "not deleted" and then the data. */
                fseek(h->fp, -1, SEEK_CUR);
                fputc(' ', h->fp); /* ensure not deleted */
                /* write fields */
                for (int f = 0; f < h->field_count; f++)
                {
                    int size = h->fields[f].field_size;
                    /* Truncate if too long, pad if too short, etc. Here we do a minimal approach. */
                    char buffer[256];
                    memset(buffer, ' ', sizeof(buffer));
                    strncpy(buffer, fields[f], size);
                    fwrite(buffer, 1, size, h->fp);
                }
                fflush(h->fp);
                return true;
            }
        }
    }

    return false;
}

/* ---------------------------------------------------------------------------
 * dbf_close
 * ------------------------------------------------------------------------- */
void dbf_close(int handle)
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return;

    DBF_HANDLE* h = g_dbf_handles[handle];
    if (h->fp)
        fclose(h->fp);
    if (h->fields)
        free(h->fields);
    free(h);

    g_dbf_handles[handle] = NULL;
}

/* ---------------------------------------------------------------------------
 * dbf_compress
 *   - “Pack” the DBF by copying only active (not-deleted) records to a new file.
 * ------------------------------------------------------------------------- */
bool dbf_compress(char* filename)
{
    /* We'll do a naive approach: open existing file, read header, create a temp file,
       copy all not-deleted records, then replace the original file with the temp. */

    FILE* fp_in = fopen(filename, "rb");
    if (!fp_in)
        return false;

    /* Read the first 32 bytes for the header, then read field descriptors until 0x0D */
    unsigned char header[32];
    if (fread(header, 1, 32, fp_in) != 32)
    {
        fclose(fp_in);
        return false;
    }

    int recordCount = (int)read_le32(&header[4]);
    int headerSize = (int)read_le16(&header[8]);
    int recordSize = (int)read_le16(&header[10]);
    long fieldDescPos = 32;

    /* Read field descriptors into memory until 0x0D or we reach headerSize-1 */
    unsigned char fieldDesc[32];
    int fieldDescCount = 0;
    /* We store them in a dynamic array for rewriting later. */
    unsigned char* fieldsBlock = NULL;
    while (1)
    {
        long pos = ftell(fp_in);
        if (pos >= (headerSize - 1))
            break;

        if (fread(fieldDesc, 1, 32, fp_in) != 32)
            break;
        if (fieldDesc[0] == 0x0D)
        {
            /* end of field descriptors */
            break;
        }
        fieldDescCount++;
        /* append these 32 bytes to fieldsBlock */
        size_t oldSize = (fieldDescCount - 1) * 32;
        size_t newSize = fieldDescCount * 32;
        fieldsBlock = (unsigned char*)realloc(fieldsBlock, newSize);
        memcpy(fieldsBlock + oldSize, fieldDesc, 32);
    }

    /* Now we have the main header, and fieldDescCount descriptors in fieldsBlock. */
    /* Create a temp file. */
    char tempName[1024];
    snprintf(tempName, sizeof(tempName), "%s.temp", filename);
    FILE* fp_out = fopen(tempName, "wb");
    if (!fp_out)
    {
        free(fieldsBlock);
        fclose(fp_in);
        return false;
    }

    /* We'll rewrite the header later with updated record count. For now, keep it as is. */
    fwrite(header, 1, 32, fp_out);

    /* Write out the field descriptors. */
    if (fieldsBlock && fieldDescCount > 0)
    {
        fwrite(fieldsBlock, 1, 32 * fieldDescCount, fp_out);
    }
    /* Terminate with 0x0D */
    fputc(0x0D, fp_out);

    /* We'll copy active records, track how many active we keep. */
    int newCount = 0;
    /* Seek to data in input file. */
    fseek(fp_in, headerSize, SEEK_SET);

    unsigned char* recordBuf = (unsigned char*)malloc(recordSize);
    for (int i = 0; i < recordCount; i++)
    {
        if (fread(recordBuf, 1, recordSize, fp_in) != (size_t)recordSize)
            break;

        /* Check if deleted flag */
        if (recordBuf[0] != '*')
        {
            /* copy to out */
            fwrite(recordBuf, 1, recordSize, fp_out);
            newCount++;
        }
    }

    /* Free memory, close files. */
    free(recordBuf);
    free(fieldsBlock);
    fclose(fp_in);

    /* Now go back to the beginning of fp_out to update record count. */
    fseek(fp_out, 4, SEEK_SET);
    /* write newCount in little-endian */
    unsigned char cntBuf[4];
    cntBuf[0] = (unsigned char)(newCount & 0xFF);
    cntBuf[1] = (unsigned char)((newCount >> 8) & 0xFF);
    cntBuf[2] = (unsigned char)((newCount >> 16) & 0xFF);
    cntBuf[3] = (unsigned char)((newCount >> 24) & 0xFF);
    fwrite(cntBuf, 1, 4, fp_out);

    fclose(fp_out);

    /* Rename files: remove the old, rename temp to the original. */
    remove(filename);
    rename(tempName, filename);

    return true;
}

/* ===========================================================================
 * dbf_creat()
 *   Creates a new DBF file with the specified fields. The file will have
 *   zero records initially, and remain open for subsequent dbf_write calls.
 *
 *   Return: handle (>= 0) on success, or -1 on failure.
 * =========================================================================*/
int dbf_creat(const char* filename, int field_count, FIELD_DEF* fielddefs)
{
    /* Open file in "wb+" mode so we can write the header and also read/write later */
    FILE* fp = fopen(filename, "wb+");
    if (!fp)
    {
        fprintf(stderr, "Cannot create DBF file: %s\n", filename);
        return -1;
    }

    /* Build a DBF_HANDLE */
    DBF_HANDLE* h = (DBF_HANDLE*)calloc(1, sizeof(DBF_HANDLE));
    if (!h)
    {
        fclose(fp);
        return -1;
    }

    h->fp = fp;
    h->field_count = field_count;
    /* Copy the field definitions into h->fields */
    h->fields = (FIELD_DEF*)malloc(field_count * sizeof(FIELD_DEF));
    if (!h->fields)
    {
        fclose(fp);
        free(h);
        return -1;
    }
    memcpy(h->fields, fielddefs, field_count * sizeof(FIELD_DEF));

    /* Compute record_size = 1 byte for delete flag + sum of all field sizes */
    int recSize = 1; /* delete flag */
    for (int i = 0; i < field_count; i++)
    {
        recSize += h->fields[i].field_size;
    }
    h->record_size = recSize;

    /* header_size = 32 (main header) + 32 bytes per field + 1 for 0x0D terminator */
    h->header_size = 32 + (field_count * 32) + 1;

    /* Initially, record_count=0, total_recs=0, curr_rec=0 (no data yet) */
    h->record_count = 0;
    h->total_recs = 0;
    h->curr_rec = 0;

    /* -----------------------------------------------------------------------
     * WRITE THE HEADER (32 bytes)
     * -----------------------------------------------------------------------
     * For simplicity, we do a minimal DBF III-like header:
     *
     * offset 0:  1 byte - Version (0x03 = dBASE III)
     * offset 1:  3 bytes - Last update YY MM DD (we can set them to 0 for now)
     * offset 4:  4 bytes - Number of records (0 for now)
     * offset 8:  2 bytes - Position of first data record (header_size)
     * offset 10: 2 bytes - Length of one record (recSize)
     * offset 12-31: Reserved or zero
     * ----------------------------------------------------------------------*/
    unsigned char header[32];
    memset(header, 0, 32);

    header[0] = 0x03; /* dBASE III version */
    /* We won't bother setting a real date in bytes [1..3] here. */

    /* We'll fill in fields [4..7], [8..9], [10..11] below by writing LE. */
    /* Write to a temp buffer, then we'll fwrite. Or do it directly: */
    /* number of records = 0 */
    /* position of first data record = h->header_size */
    /* length of one data record = h->record_size */

    /* We'll just write them after we do fwrite(header,...). So for clarity: */
    fwrite(header, 1, 32, fp);

    /* Now overwrite the needed parts in-place */
    fseek(fp, 4, SEEK_SET);
    write_le32(0, fp);                              /* record count = 0 */
    write_le16((uint16_t)h->header_size, fp);       /* position of first data record */
    write_le16((uint16_t)h->record_size, fp);       /* length of one data record */

    /* Go to offset 32 to write field descriptors */
    fseek(fp, 32, SEEK_SET);

    /* -----------------------------------------------------------------------
     * WRITE FIELD DESCRIPTORS (32 bytes each)
     *   offset [0..10]: field name (ASCII, 0-padded)
     *   offset 11: field type (we'll assume 'C' for character in this example)
     *   offset 12..15: field data address in memory (ignore for simplicity)
     *   offset 16: field length
     *   offset 17: decimal count (0 for character)
     *   offset 18..31: reserved
     * ----------------------------------------------------------------------*/
    for (int i = 0; i < field_count; i++)
    {
        unsigned char fieldDesc[32];
        memset(fieldDesc, 0, 32);

        /* field name up to 11 chars, 0-padded */
        strncpy((char*)fieldDesc, h->fields[i].field_name, 11);

        /* field type = 'C' for character (very simplistic) */
        fieldDesc[11] = 'C';

        /* field length at offset 16 */
        fieldDesc[16] = (unsigned char)h->fields[i].field_size;

        /* decimal count at offset 17 = 0 for character fields */
        fieldDesc[17] = 0;

        /* write the 32-byte descriptor */
        fwrite(fieldDesc, 1, 32, fp);
    }

    /* A single 0x0D to mark end of field descriptors */
    fputc(0x0D, fp);

    /* Ensure everything is written */
    fflush(fp);

    /* Now place the handle in the global array */
    int handle_id = find_free_handle_slot();
    if (handle_id < 0)
    {
        fprintf(stderr, "No free DBF handle slots\n");
        free(h->fields);
        free(h);
        fclose(fp);
        return -1;
    }

    g_dbf_handles[handle_id] = h;
    return handle_id;
}

/* ---------------------------------------------------------------------------
 * Example update to dbf_write so that it can append new records if needed
 * ------------------------------------------------------------------------- */
static bool goto_record(DBF_HANDLE* h, int nth);

#ifdef MOOO
bool dbf_write(int handle, char* fields[])
{
    if (handle < 0 || handle >= MAX_DBF_HANDLES || !g_dbf_handles[handle])
        return false;

    DBF_HANDLE* h = g_dbf_handles[handle];

    /*
     * If h->curr_rec <= h->total_recs, we overwrite the existing
     * active record. If h->curr_rec = total_recs+1, we append a new record.
     * If h->curr_rec > total_recs+1, it's invalid for this simple demo.
     */
    if (h->curr_rec < 1)
    {
        /* No current record set? Let's just append as record #1 if nothing else. */
        h->curr_rec = h->total_recs + 1;
    }
    if (h->curr_rec > h->total_recs + 1)
        return false; /* out of range for a simple approach */

    bool append = (h->curr_rec == h->total_recs + 1);

    /* If appending, physically go to the end of the file */
    if (append)
    {
        /* The new record will be physically after h->record_count records. */
        /* Move file pointer to the end-of-file (or direct offset) */
        fseek(h->fp, 0, SEEK_END);

        h->record_count++;
        h->total_recs++;
        /* Update the DBF header’s record count on disk */
        fseek(h->fp, 4, SEEK_SET);
        write_le32(h->record_count, h->fp);
        fflush(h->fp);

        /* Now position to the place where the new record starts. We should already be at EOF,
           but let's do it carefully in case the DBF had some weird offset. */
        long offset = h->header_size + (long)(h->record_count - 1) * h->record_size;
        fseek(h->fp, offset, SEEK_SET);
    }
    else
    {
        /* Overwrite existing record -> find the (curr_rec)-th active record physically
         * in a naive way. This is the original code from the prior example.
         */
        int active_found = 0;
        for (int r = 1; r <= h->record_count; r++)
        {
            if (!goto_record(h, r))
                return false;

            char deleteFlag = 0;
            if (fread(&deleteFlag, 1, 1, h->fp) != 1)
                return false;

            if (deleteFlag != '*')
            {
                active_found++;
                if (active_found == h->curr_rec)
                {
                    /* Overwrite from this point on. Seek back 1 byte. */
                    fseek(h->fp, -1, SEEK_CUR);
                    break; /* We are now positioned at the start of this record */
                }
            }
        }
    }

    /* Write a space (0x20) for "not deleted" flag. */
    fputc(' ', h->fp);

    /* Write each field’s data (truncate or pad as needed). */
    for (int f = 0; f < h->field_count; f++)
    {
        int size = h->fields[f].field_size;
        char buffer[256];
        memset(buffer, ' ', sizeof(buffer)); /* pad with spaces */
        strncpy(buffer, fields[f], size);
        fwrite(buffer, 1, size, h->fp);
    }

    fflush(h->fp);
    return true;
}
#endif

/******************************************************************************
 * Example usage (comment out if not needed):
 *****************************************************************************/

int main(void)
{
    int field_count;
    FIELD_DEF* fields;
    int handle = dbf_open("example.dbf", &field_count, &fields);
    if (handle < 0)
    {
        printf("Failed to open DBF\n");
        return 1;
    }

    printf("Opened DBF: total active records = %d\n", dbf_total_recs(handle));

    // Example read
    if (dbf_total_recs(handle) > 0)
    {
        char* recordFields[100]; // Enough for 100 fields
        // For each field, we need a buffer large enough:
        for (int i = 0; i < field_count; i++)
        {
            // +1 for null terminator
            recordFields[i] = (char*)malloc(fields[i].field_size + 1);
        }

        if (dbf_read(handle, recordFields))
        {
            printf("Record %d:\n", dbf_currrecno(handle));
            for (int i = 0; i < field_count; i++)
            {
                printf("  Field[%d] (%s): '%s'\n",
                       i, fields[i].field_name, recordFields[i]);
            }
        }

        // Clean up
        for (int i = 0; i < field_count; i++)
        {
            free(recordFields[i]);
        }
    }

    dbf_close(handle);

    // Example compress
    if (dbf_compress("example.dbf"))
        printf("Compression succeeded.\n");
    else
        printf("Compression failed.\n");

    return 0;
}
