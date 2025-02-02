cimport cython

@cython.final
cdef class UpdateRequest(BaseRequest):
    cdef int encode_body(self, WriteBuffer buffer) except -1:
        return encode_request_update(buffer, self.space, self.index,
                                     self.key, self.operations, <bint> False)

cdef char *encode_update_ops(WriteBuffer buffer,
                             char *p, list operations,
                             SchemaSpace space) except NULL:
    cdef:
        char *begin
        uint32_t ops_len, op_len
        bytes str_temp
        char *str_c
        ssize_t str_len

        char *op_str_c
        ssize_t op_str_len
        char op
        uint32_t extra_length

        char *field_no
        object field_no_obj
        ssize_t field_no_len
        bytes field_temp
        
        uint32_t splice_position, splice_offset

    begin = NULL

    if operations is not None:
        ops_len = <uint32_t> cpython.list.PyList_GET_SIZE(operations)
    else:
        ops_len = 0

    p = buffer.mp_encode_array(p, ops_len)
    if ops_len == 0:
        return p

    for operation in operations:
        if not isinstance(operation, (list, tuple)):
            raise TypeError(
                'Single operation must be a tuple or list')

        op_len = <uint32_t> cpython.list.PyList_GET_SIZE(operation)
        if op_len < 3:
            raise IndexError(
                'Operation length must be at least 3')

        op_type_str = operation[0]
        if isinstance(op_type_str, str):
            str_temp = encode_unicode_string(op_type_str, buffer._encoding)
        elif isinstance(op_type_str, bytes):
            str_temp = <bytes> op_type_str
        else:
            raise TypeError(
                'Operation type must of a str or bytes type')

        field_no_obj = operation[1]
        if isinstance(field_no_obj, str):
            field_temp = encode_unicode_string(field_no_obj, buffer._encoding)
        elif isinstance(field_no_obj, bytes):
            field_temp = <bytes> field_no_obj
        else:
            raise TypeError(
                'Field type must of a str or bytes type')
        
        cpython.bytes.PyBytes_AsStringAndSize(field_temp,
                                              &field_no,
                                              &field_no_len)
        max_field_len = 1 \
                       + 1 \
                       + mp_sizeof_str(<uint32_t> field_no_len) \
                       + 1
     
        buffer.ensure_allocated(max_field_len)
    
        cpython.bytes.PyBytes_AsStringAndSize(str_temp, &op_str_c,
                                              &op_str_len)
        op = <char> 0
        if op_str_len == 1:
            op = op_str_c[0]

        if op == tarantool.IPROTO_OP_ADD \
                or op == tarantool.IPROTO_OP_SUB \
                or op == tarantool.IPROTO_OP_AND \
                or op == tarantool.IPROTO_OP_XOR \
                or op == tarantool.IPROTO_OP_OR \
                or op == tarantool.IPROTO_OP_DELETE:
            op_argument = operation[2]
            if not isinstance(op_argument, int):
                raise TypeError(
                    'int argument required for '
                    'Arithmetic and Delete operations'
                )

            p = mp_encode_array(p, 3)
            p = mp_encode_str(p, op_str_c, 1)
            p = mp_encode_str(p, field_no, <uint32_t> field_no_len)
            buffer._length += (p - begin)
            p = buffer.mp_encode_obj(p, op_argument)
        
        elif op == tarantool.IPROTO_OP_INSERT \
                or op == tarantool.IPROTO_OP_ASSIGN:
            op_argument = operation[2]

            p = mp_encode_array(p, 3)
            p = mp_encode_str(p, op_str_c, 1)
            p = mp_encode_str(p, field_no, <uint32_t> field_no_len)
            buffer._length += (p - begin)
            p = buffer.mp_encode_obj(p, op_argument)
        
        else:
            raise TypeError(
                'Unknown update operation type `{}`'.format(op_type_str))
    return p

cdef int encode_request_update(WriteBuffer buffer,
                               SchemaSpace space, SchemaIndex index,
                               key_tuple, list operations,
                               bint is_upsert) except -1:
    cdef:
        char *begin
        char *p
        uint32_t body_map_sz
        uint32_t max_body_len
        uint32_t space_id, index_id
        uint32_t key_of_tuple, key_of_operations
        Metadata metadata
        bint default_fields_none

    space_id = space.sid
    index_id = index.iid

    if not is_upsert:
        key_of_tuple = tarantool.IPROTO_KEY
        key_of_operations = tarantool.IPROTO_TUPLE
        metadata = index.metadata
        default_fields_none = False
    else:
        key_of_tuple = tarantool.IPROTO_TUPLE
        key_of_operations = tarantool.IPROTO_OPS
        metadata = space.metadata
        default_fields_none = True

    body_map_sz = 3 + <uint32_t> (index_id > 0)
    # Size description:
    # mp_sizeof_map(body_map_sz)
    # + mp_sizeof_uint(TP_SPACE)
    # + mp_sizeof_uint(space)
    max_body_len = 1 \
                   + 1 \
                   + 9

    if index_id > 0:
        # + mp_sizeof_uint(TP_INDEX)
        # + mp_sizeof_uint(index)
        max_body_len += 1 + 9

    max_body_len += 1  # + mp_sizeof_uint(TP_KEY)
    max_body_len += 1  # + mp_sizeof_uint(TP_TUPLE)

    buffer.ensure_allocated(max_body_len)

    p = begin = &buffer._buf[buffer._length]
    p = mp_encode_map(p, body_map_sz)
    p = mp_encode_uint(p, tarantool.IPROTO_SPACE_ID)
    p = mp_encode_uint(p, space_id)

    if index_id > 0:
        p = mp_encode_uint(p, tarantool.IPROTO_INDEX_ID)
        p = mp_encode_uint(p, index_id)
    buffer._length += (p - begin)

    p = buffer.mp_encode_uint(p, key_of_tuple)
    p = encode_key_sequence(buffer, p, key_tuple, metadata, default_fields_none)

    p = buffer.mp_encode_uint(p, key_of_operations)
    p = encode_update_ops(buffer, p, operations, space)
