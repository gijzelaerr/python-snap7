Error Message Reference
=======================

The following table maps common S7 error strings to their likely cause and fix.

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Error message
     - Likely cause
     - Fix
   * - ``CLI : function refused by CPU (Unknown error)``
     - PUT/GET communication is not enabled on the PLC, or the data block
       still has optimized block access enabled.
     - Enable PUT/GET in TIA Portal and disable optimized block access on each
       DB. See :doc:`tia-portal-config`.
   * - ``CPU : Function not available``
     - The requested function is not supported on this PLC model. S7-1200 and
       S7-1500 PLCs restrict certain operations.
     - Check Siemens documentation for your PLC model. Some functions are only
       available on S7-300/400.
   * - ``CPU : Item not available``
     - Wrong DB number, the DB does not exist, or the address is out of range.
     - Verify the DB number exists on the PLC and that the offset and size are
       within bounds.
   * - ``CPU : Address out of range``
     - Reading or writing past the end of a DB or memory area.
     - Check the DB size in TIA Portal and ensure ``start + size`` does not
       exceed it.
   * - ``CPU : Function not authorized for current protection level``
     - The PLC has password protection enabled.
     - Remove or lower the protection level in TIA Portal under
       Protection & Security.
   * - ``ISO : An error occurred during recv TCP : Connection timed out``
     - Network issue: PLC is unreachable, a firewall is blocking port 102, or
       the PLC is not responding.
     - Check network connectivity (``ping``), verify firewall rules, and ensure
       the PLC is powered on and reachable.
   * - ``ISO : An error occurred during send TCP : Connection timed out``
     - Same as above.
     - Same as above.
   * - ``TCP : Unreachable peer``
     - The PLC is not reachable on the network.
     - Verify IP address, subnet, and routing. Ensure the PLC Ethernet port is
       connected and configured.
   * - ``TCP : Connection reset`` / Socket error 32 (broken pipe)
     - The connection to the PLC was lost unexpectedly.
     - The PLC may have been restarted, the cable disconnected, or another
       client took over the connection. See :doc:`connection-issues`.
