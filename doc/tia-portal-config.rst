.. _tia-portal-config:

TIA Portal Configuration
=========================

S7-1200 and S7-1500 PLCs require specific configuration in TIA Portal before
python-snap7 can communicate with them. Without these settings, you will get
``CLI : function refused by CPU`` errors.

.. contents:: On this page
   :local:
   :depth: 2


Step 1: Enable PUT/GET Communication
-------------------------------------

1. Open your project in TIA Portal.
2. In the project tree, double-click on the PLC device.
3. Go to **Properties** > **Protection & Security** > **Connection mechanisms**.
4. Check **Permit access with PUT/GET communication from remote partner**.
5. Compile and download to the PLC.

.. warning::

   This setting allows any network client to read and write PLC memory without
   authentication. Only enable this on isolated industrial networks.


Step 2: Disable Optimized Block Access
---------------------------------------

This must be done for **each** data block you want to access:

1. In the project tree, right-click on the data block (e.g., DB1).
2. Select **Properties**.
3. Go to the **Attributes** tab.
4. **Uncheck** "Optimized block access".
5. Click OK.
6. Compile and download to the PLC.

.. warning::

   Changing the "Optimized block access" setting reinitializes the data block,
   which resets all values in that DB to their defaults. Do this before
   commissioning, or back up your data first.


Step 3: Compile and Download
-----------------------------

After making both changes:

1. Compile the project (**Build** > **Compile**).
2. Download to the PLC (**Online** > **Download to device**).
3. The PLC may need to restart depending on the changes.
