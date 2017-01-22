include "const.pxi"

include "cmsgpuck.pxd"
include "python.pxd"

include "buffer.pxd"
include "request.pxd"
include "response.pxd"
include "encdec.pxd"

include "coreproto.pxd"


cdef class BaseProtocol(CoreProtocol):
    cdef:
        object loop
        str username
        str password
        bint fetch_schema
        object connected_fut
        object on_connected_lost_cb
        
        object _on_request_completed_cb
        object _on_request_timeout_cb
        
        uint64_t _sync
        
    cdef void _set_connection_ready(self)

    cdef _do_auth(self, str username, str password)
    cdef _do_fetch_schema(self)
    
    cdef uint64_t _next_sync(self)
    
    cdef object _new_waiter_for_request(self, Request req, float timeout)
    cdef object _execute(self, Request req, float timeout)
