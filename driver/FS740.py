import visa

class FS740:
    def __init__(self, resource_manager, resource_name, protocol):
        self.rm = resource_manager
        if protocol == 'RS232':
            self.instr = self.rm.open_resource(resource_name)
            self.instr.parity = visa.constants.Parity.none
            self.instr.data_bits = 8
            self.instr.write_termination = '\r\n'
            self.instr.read_termination = '\r\n'
            self.instr.baud_rate = 115200
        elif protocol == 'TCP':
            self.instr = self.rm.open_resource("TCPIP::{0}::5025::SOCKET".format(resource_name))
            self.instr.write_termination = '\r\n'
            self.instr.read_termination = '\r\n'

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.instr.close()

    def query(self, cmd):
        return self.instr.query(cmd)

    def set(self, cmd):
        self.instr.write(cmd)

    def ReadValue(self, ):
        return

    def VerifyOperation(self, ):
        return self.ReadIDN().split(',')[1]

    #################################################################
    ##########  Common IEEE-448.2 Commands                 ##########
    #################################################################

    def CLS(self):
        """
        This command immediately clears all status registers as well
        as the SYST:ERR queue.
        Manual p.91
        """
        self.set("*CLS")

    def ESE(self, value):
        """
        Set the Standard Event Status Enable register to <value>. The
        value may range from 0 to 255. Bits set in this register cause
        ESR (in *STB) to be set when the corresponding bit is set in
        the *ESR register.
        Manual p.91
        """
        self.write("*ESE {0}".format(value))

    def ReadESE(self):
        return self.query("*ESE?")

    def ReadESR(self):
        """
        Query the Standard Event Status Register. After the query,
        the returned bits of the *ESR register are cleared. The bits
        in the ESR register have the following meaning:

        bit : name : meaning
        0   : OPC  : operation complete
        1   :      :
        2   : QYE  : Query error occured
        3   : DDE  : Device dependent error occured
        4   : EXE  : Excecution error. Command failed to execute
                     correctly because a parameter was invalid
        5   : CME  : Command error. The parser detected a syntax
                     error.
        6   :      :
        7   : PON  : Power on. The unit has been power cycled.
        """
        return self.query("*ESR?")

    def ReadOPC(self):
        """
        The set form sets the OPC flag in the *ESR register when all
        prior commands have completed. The query form returns ‘1’ when
        all prior commands have completed, but does not affect the
        *ESR register.
        Manual p.92
        """
        return self.query("*OPC?")

    def ReadOPT(self):
        """
        The query returns a comma separated list of the four possible
        installed options in the following order: installed timebase,
        top rear panel board, middle rear panel board, and bottom rear
        panel board.

        type     : option   : value
        Timebase : TCXO     : 0
                 : OCXO     : 1
                 : Rb       : 2
        Board    : 10 MHz   : A
                 : Sine/Aux : B
                 : Pulse    : C
                 : None     : D
        Manual p.92

        2,A,A,A -> Rb timebase, 3x 10 MHz distribution slots.
        """
        return self.query("*OPT?")

    def ReadIDN(self):
        """
        Query the instrument identification string.
        Manual p.92
        """
        return self.query("*IDN?")

    def PSC(self, value):
        """
        Set the Power-on Status Clear flag to <value>. The Power-on
        Status Clear flag is stored in nonvolatile memory in the unit,
        and thus, maintains its value through power-cycle events. If
        the value of the flag is 0, then the Service Request Enable
        and Standard Event Status Enable Registers (*SRE, *ESE) are
        stored in non-volatile memory, and retain their values through
        powercycle events. If the value of the flag is 1, then these
        two registers are cleared upon power-cycle.
        Manual p.93
        """
        self.write("*PSC {0}".format(value))

    def ReadPSC(self):
        return self.query("*PSC?")

    def RCL(self, location):
        """
        Recall instrument settings from <location>. The <location> may
        range from 0 to 9. Locations 1 to 9 are for arbitrary use.
        Location 0 is reserved for the recall of default instrument
        settings.
        Manual p.93
        """
        assert type(location) == int, 'location invalid type'
        assert (location >= 0) and (location <= 9), \
        'location out of range'
        self.set("*RCL {0}".format(location))

    def RST(self):
        """
        Reset the instrument to default settings. This is equivalent
        to *RCL 0.
        Manual p.93
        """
        self.set("*RST")

    def SRE(self, value):
        """
        Set the Service Request Enable register to <value>. Bits set
        in this register cause the FS740 to generate a service request
        when the corresponding bit is set in the serial poll status
        register, *STB.
        Manual p.94
        """
        self.write("*SRE {0}".format(value))

    def ReadSRE(self):
        return self.query("*SRE?")

    def ReadSTB(self):
        """
        Query the standard IEEE 488.2 serial poll status byte. The bits
        in the STB register have the following meaning:

        bit : meaning
        0   : reserved
        1   : GPS status summary bit
        2   : Error queue is not empty
        3   : Questionable status summary bit
        4   : Message available, MAV
        5   : ESR status summary bit
        6   : MSS master summary bit
        7   : Operational status summary bit

        Manual p.94
        """
        return self.query("*STB?")

    def SAV(self, location):
        """
        Save instrument settings to <location>. The <location> may
        range from 0 to 9. However, location 0 is reserved for
        current instrument settings. It will be overwritten after each
        front panel key press.
        Manual p.93
        """
        assert type(location) == int, 'location invalid type'
        assert (location >= 0) and (location <= 9), \
        'location out of range'
        self.set("*SAV {0}".format(location))

    def WAI(self):
        """
        The instrument will not process further commands until all
        prior commands including this one have completed.
        Manual p.95
        """
        self.set("*WAI")

    #################################################################
    #######  Measurement commands                             #######
    #################################################################

    @staticmethod
    def ValidateFrequency(freq):
        if freq in ['DEF', 'MIN', 'MAX']:
            return
        assert (type(freq) == float) or (type(freq) == int),\
        'freq invalid type'
        assert (freq >= 1e-1) and (freq <= 1.5e8), 'freq out of range'

    @staticmethod
    def ValidateResolution(res):
        if res in ['DEF', 'MIN', 'MAX']:
            return
        assert type(res) == int, 'res invalid type'
        assert (res >= 1e-16) and (res <= 1.5e-2), 'res out of range'

    def MeasureFrequency(self, expected = 'DEF', resolution = 'DEF',
                          front = True):
        """
        Configures hardware for a frequency measurement and
        immediately triggers a measurement and sends the result to the
        output buffer. The first parameter is optional and informs the
        instrument of the expected frequency of the signal. The second
        parameter is also optional. It sets the requested resolution
        of the measurement. Neither parameter is used directly by the
        FS740. Instead the ratio of the resolution to the expected
        frequency is used to set the gate time for the measurement. If
        the parameters are omitted, a gate time of 0.1 second is used
        which corresponds to approximately 11 digits of precision.
        Measurements are returned as floating point values in units of
        Hz. If ameasurement times out NAN is returned.
        Manual p.96
        """
        self.ValidateFrequency(expected)
        self.ValidateResolution(resolution)
        return self.query("MEAS{0}:FREQ? {1}, {2}".format(
            1 if front else 2, expected, resolution))

    def MeasureTime(self, front = True):
        """
        Trigger default time measurement
        Manual p.96
        """
        return self.query("MEAS{0}:TIM?".format(1 if front else 2))

    def ReadConfigure(self, front = True):
        """
        Read current measurement configuration.
        Manual p.97
        """
        return self.query("CONF{0}?".format(1 if front else 2))

    def ConfigureFrequency(self, freq = 'DEF', res = 'DEF',
                           front = True):
        """
        Configure hardware for frequency measurement.
        Manual p.97
        """
        self.ValidateFrequency(freq)
        self.ValidateResolution(res)
        self.set("CONF{0}:FREQ {1}, {2}".format(1 if front else 2,
                                               freq, res))

    def ConfigureTime(self, front = True):
        """
        Configures hardware for a measurement of time and immediately
        triggers a measurement and sends the result to the output buffer.
        Results are returned with a READ command. A single result consists
        of 11 comma separated integer values in the following order:
        timing metric, year, month, day, hour, minute, seconds,
        milliseconds, microseconds, nanoseconds, picoseconds. The timing
        metric is a copy of the questionable status register at the time
        of the measurement.
        Manual p.98
        """
        self.set("CONF{0}:TIM".format(1 if front else 2))


    def Read(self, front = True):
        """
        Trigger a measurement using the current configuration and read
        the result. See commands MEASure:FREQuency and MEASure:TIMe for
        details on the format of results returned. When the sample size
        is greater than one, results are separated from each other by
        commas ( , ).
        Manual p.98
        """
        return self.query("READ{0}?".format(1 if front else 2))

    def Initiate(self, front = True):
        """
        Trigger a measurement using the current configuration but
        leave results in internal memory. The internal memory has
        enough space to store the last 250,000 measurements. The
        user should send the FETCh command to retrieve the results
        from internal memory. Alternatively, the user may use commands
        in the DATA subsystem to read only a portion of the results.
        Manual p.98
        """
        self.set("INIT{0}".format(1 if front else 2))

    def Fetch(self, front = True):
        """
        Copy results stored in the internal buffer to the output buffer
        for reading. Like the READ command, this command will not
        complete until all measurements have completed. See commands
        MEASure:FREQuency and MEASure:TIMe for details on the format of
        results returned. When the sample size is greater than one,
        results are separated from each other by commas ( , ).
        Manual p.99
        """
        return self.query("FETC{0}?".format(1 if front else 2))

    def Abort(self, front = True):
        """
        Stop any measurement in progress and discard any results
        produced.
        Manual p.99
        """
        self.set("ABOR{0}".format(1 if front else 2))

    def Stop(self, front = True):
        """
        Stop any measurement in progress, but do not discard any
        results produced.
        Manual p.99
        """
        self.set("STOP{0}".format(1 if front else 2))

    #################################################################
    ##########  Calculate Subsystem                        ##########
    #################################################################
    """
    Commands in the Calculate Subsystem can apply to either the front
    or rear input. The user selects the input by optionally appending
    a 1 or 2 to the CALCulate keyword. When the suffix is 1 or
    omitted, the front input is selected. When the suffix is 2, the
    rear input is selected.
    """

    def CalculateFilter(self, filtersetting):
        """
        The first definition changes input filter for frequency
        measurements. The second definition queries the current input
        filter. There are two filter options: NONE and FAST. If NONE
        is selected, then just two time tags are used to generate a
        frequency measurement, one at the beginning of the gate
        interval and one at the end. When the FAST filter is
        selected, up to 625 time tags are averaged together at the
        beginning of the gate interval to produce an average starting
        time tag. Another 625 time tags are averaged together at the
        end of the gate interval to produce an average ending time tag.
        These two averaged time tags are used to compute a frequency
        measurement. The benefit of this filter is that it is effective
        in removing broadband noise inherent in the measurement. Noise
        can be reduced by more than a factor of 10 with the use of
        this filter. The default filter is FAST and it is the
        recommended setting for most measurements.
        Manual p.100
        """
        assert filtersetting in ['FAST', 'NONE'], \
        'filter invalid value'
        self.set("CALC:FILT {0}".format(filtersetting))

    def ReadCalculateFilter(self):
        return self.query("CALC:FILT?")

    def SetCalculateReference(self, freq = 'DEF', front = True):
        """
        For each frequency measurement, the reference frequency is
        subtracted from the measured frequency to produce the final
        result. This enables one to monitor the deviation of the
        frequency from a specified target value rather than the
        absolute frequency itself. The first definition sets the
        reference frequency to <frequency>. If <frequency> is omitted,
        it is set to the value of the most recent measurement. The
        second definition queries the current reference frequency. The
        default reference frequency is 0 Hz.
        Manual p.100
        """
        self.ValidateFrequency(freq)
        self.set("CALC{0}:REF {1}".format(1 if front else 2, freq))

    def ReadCalculateReference(self, front = True):
        return self.query("CALC{0}:REF?".format(1 if front else 2))

    def CalculateStability(self, front = True):
        """
        This command computes the frequency stability, or Allan
        deviation, of all frequency measurements for time intervals
        from 10 ms to 50 million seconds in a 1, 2, 5 sequence and
        returns them as a comma delimited list of relative Allan
        deviations.
        Manual p.101

        Returns 10 ms, 20 ms, 50 ms, 100 ms, ... , 5e7 s.
        """
        return self.query("CALC{0}:STAB?".format(1 if front else 2))

    def CalculateStatistics(self, front = True):
        """
        This command computes some basic statistics of the current
        measurement and returns the following values in a comma
        separated list: the mean, the Allan deviation, the minimum,
        the maximum, and the number of measurements made.
        Manual p.101

        Returns mean, ASD, min, max and # measurements.
        """
        return self.query("CALC{0}:STAT?".format(1 if front else 2))

    #################################################################
    ##########  Data Subsystem                             ##########
    #################################################################

    def DataCount(self, front = True):
        """
        This command returns the total number of measurements
        completed so far.
        Manual p.102
        """
        return int(self.query("DATA{0}:COUN?".format(
            1 if front else 2)))

    def DataPoints(self, front = True):
        """
        This command returns the total number of measurements stored
        in internal memory.
        Manual p.102
        """
        return self.query("DATA{0}:POIN?".format(1 if front else 2))

    def DataRead(self, index, count, front = True):
        """
        This command returns <count> measurements stored in internal
        memory, starting with the one located at <index>.
        Manual p.103
        """
        assert type(index) == int, 'index invalid type'
        assert type(count) == int, 'count invalid type'
        assert index >= 0, 'index out of range'
        assert count >= 0, 'count out of range'
        return self.query("DATA{0}:READ? {1}, {2}".format(
            1 if front else 2, index, count))

    def DataRemove(self, count, front = True):
        """
        This command returns the first <count> measurements stored in
        internal memory and removes them from memory.
        Manual p.103
        """
        assert (type(count) == int), 'count invalid type'
        assert count >= 0, 'count out of range'
        return self.query("DATA{0}:REM? {1}".format(
            1 if front else 2, count))

    #################################################################
    ##########  GPS Subsystem                              ##########
    #################################################################
    """
    Not implemented:
        GPS:CONFig:MODe
        GPS:CONFig:SAVe
        GPS:CONFig:SURVey:Mode
        GPS:CONFig:SURVey:FIXes
        GPS:CONFig:ALIGnment
        GPS:CONFig:QUALity
        GPS:CONFig:ADELay
        GPS:POSition:SURVey:DELete
        GPS:POSition:SURVey:PROGress
        GPS:POSition:SURVey:SAVe
        GPS:POSition:SURVey:STARt
        GPS:POSition:SURVey:STATe
        GPS:UTC:OFFSet
    """
    def GPSConfigMode(self):
        """
        Query the GPS Config Mode.
        Returns anti-jamming, elevation mask and signal mask:
         - anti-jamming is a Boolean value
         - elevation mask is the elevation angle in radians below which satellites
           are ignored in over determined clock mode
         - signal mask is the minimum signal level in dbHz below which satellites
           are ignored in over determined clock mode
        """
        return self.query("GPS:CON:MOD?")

    def GPSPosition(self):
        """
        Query the GPS position.
        Returns latitude, longitude and altitude.
        Latitude is specified in radians, with positive values
        indicating north, and negative values indicating south.
        Longitude is specified in radians, with positive values
        indicating east, and negative values indicating west.
        Altitude is specified in meters above average sea levels.
        Manual p.106
        """
        return self.query("GPS:POS?")

    def GPSPositionHoldState(self):
        """
        Query whether the GPS receiver is in position hold mode where
        all satellites are being used for maximum timing performance.
        0: min performance
        1: hold mode, max performance
        Manual p.107
        """
        return self.query("GPS:POS:HOLD:STAT?")

    def GPSSatelliteTracking(self):
        """
        Query which GPS satellites are being tracked by the receiver.
        The query returns the number of satellites being tracked,
        followed by the IDs of the satellites as a comma ( , )
        separated list.
        Manual p.108
        """
        return self.query("GPS:SAT:TRAC?")

    def GPSSatelliteTrackingStatus(self):
        """
        The receiver has 20 channels for tracking satellites. This
        command returns the information shown below for each
        channel, successively.
        index: parameter
        0: Satellite ID number
        1: Acquired
        2: Ephemeris
        3: Is old
        4: Signal level in dbHz
        5: Elevation in degrees
        6: Azimuth in degrees
        7: Space vehicle type
        Manual p.109
        """
        return self.query("GPS:SAT:TRAC:STAT?")

    #################################################################
    ##########  Input Subsystem                            ##########
    #################################################################

    @staticmethod
    def ValidateMinDefMax(value):
        return value in ['MIN', 'MAX', 'DEF']

    @staticmethod
    def ValidateLevel(level):
        if self.ValidateMinDefMax(level):
            return 0
        assert type(level) in [int, float], 'level invalid type'
        assert (level >= -3.0) and (level <= 3.0), \
        'level out of range'

    def InputLevel(self, level, front = True):
        """
        Set input trigger level.
        Manual p.110
        """
        self.ValidateLevel(level)
        self.set("INP{0}:LEV {1}".format(1 if front else 2, level))

    def ReadInputLevel(self, front = True):
        """
        Read input trigger level.
        Manual p.110
        """
        return self.query("INP{0}:LEV?".format(1 if front else 2))

    def InputSlope(self, slope, front = True):
        """
        Set input slope.
        Manual p.110
        """
        assert slope in ['NEG', 'POS', 'DEF'], 'slope invalid'
        self.set("INP{0}:SLOP {1}".format(1 if front else 2, slope))

    def ReadInputSlope(self, front = True):
        """
        Read input slope.
        Manual p.110
        """
        return self.query("INP{0}:SLOP?".format(1 if front else 2))

    #################################################################
    ##########  Route Subsystem                            ##########
    #################################################################
    """
    Not implemented:
        ROUTe:OPTion

    Option not installed in CeNTREX FS740
    """

    #################################################################
    ##########  Sample Subsystem                           ##########
    #################################################################

    @staticmethod
    def ValidateCount(count):
        if count in ['DEF', 'MIN', 'MAX']:
            return
        assert type(count) == int, 'count invalid type'
        assert (count >= 1) and (count <= int(1e9)),\
        'count out of range'

    def SampleCount(self, count, front=True):
        """
        Set sample count.
        Manual p.111
        """
        self.ValidateCount(count)
        self.set("SAMP{0}:COUN {1}".format(1 if front else 2, count))

    def ReadSampleCount(self, front=True):
        self.set("SAMP{0}:COUN?".format(1 if front else 2))

    #################################################################
    ##########  Sense Subsystem                            ##########
    #################################################################

    @staticmethod
    def ValidateGate(gate):
        if gate in ['DEF', 'MIN', 'MAX']:
            return
        assert (type(gate) == float) or (type(gate) == int),\
        'gate invalid type'
        assert (gate >= 1e-2) and (gate <= 1e3), 'gate out of range'

    def SenseFrequencyGate(self, gate, front = True):
        """
        Set gate for frequency measurement.
        Manual p.111
        """
        self.ValidateGate(gate)
        self.set("SENS{0}:FREQ:GATE {1}".format(1 if front else 2,
                                                gate))

    def ReadSenseFrequencyGate(self, front = True):
        return self.query('SENS{0}:FREQ:GATE?'.format(
            1 if front else 2))

    @staticmethod
    def ValidateTimeout(timeout):
        if self.ValidateMinDefMax(timeout):
            return 0
        assert type(timeout) in [int, float], 'timeout invalid type'
        assert (timeout >= 1e-2) & (timeout <= 2e3), \
        'timeout out of range'

    def SenseFrequencyTimeout(self, timeout, front = True):
        """
        Sets time out period for frequency measurements to <timeout>
        in seconds.
        Manual p.112
        """
        self.ValidateTimeout(timeout)
        self.set("SENS{0}:FREQ:TIM {1}".format(1 if front else 2,
                                               timeout))

    def ReadSenseFrequencyTimeout(self, front = True):
        return self.query("SENS{0}:FREQ:TIM?".format(
            1 if front else 2))

    def SenseTimeBMode(self, mode, front = True):
        """
        Sets buffer mode for time measurements.
        If KFIRst (Keep First) is specified then older measurements
        are preserved and new measurements are dropped. If KLASt
        (Keep Last) is specified then older measurements are dropped
        and newer measurements are preserved. The default value is
        KLASt.
        Manual p.112
        """
        assert mode in ['KFIR', 'KLAS'], 'mode parameter invalid'
        self.set("SENS{0}:TIM:BMOD {1}".format(1 if front else 2,
                                              mode))

    def ReadSenseTimeBMode(self, front = True):
        return self.query("SENS{0}:TIM:BMOD?".format(
            1 if front else 2))

    #################################################################
    ##########  Source Subsystem                           ##########
    #################################################################

    """
    Not implemented:
        SOURce:PHASe
        SOURce:PHASe:REFerence
        SOURce:PHASe:SYNChronize
        SOURce:PHASe:SYNChronize:AUTo
        SOURce:PHASe:SYNChronize:TDELay
        SOURce3:PULSe:DCYCle
        SOURce3:PULSe:PERiod
        SOURce3:PULSe:VIEW
        SOURce3:PULSe:WIDTh
    """
    @staticmethod
    def ValidateSourceOutput(output):
        assert output in [1,2,3], 'output parameter invalid'

    @staticmethod
    def ValidateSourceFrequency(freq, output):
        if ValidateMinDefMax(freq):
            return 0
        assert type(freq) in [int, float], 'freq invalid type'
        if output == 1:
            assert (freq >= 1e-3) and (freq <= 30.1e6), \
            'frequency out of range'
        elif output == 2:
            assert (freq >= 1e-3) and (freq <= 1e6), \
            'frequency out of range'
        elif output == 3:
            assert (freq >= 1e-3) and (freq <= 25e6), \
            'frequency out of range'

    def SourceFrequency(self, freq, output):
        """
        Sets the output frequency for the selected output to <freq>
        in Hz.
        Manual p.113
        """
        self.ValidateSourceOutput(output)
        self.ValidateSourceFrequency(freq)
        self.set("SOUR{0}:FREQ {1}".format(output, freq))

    def ReadSourceFrequency(self, output):
        self.ValidateSourceOutput(output)
        return self.query("SOUR{0}:FREQ?".format(output))

    def Source2Function(self, shape):
        """
        Sets the function for the Aux output.
        Manual p.114
        """
        assert shape in ['SIN', 'TRI', 'SQU', 'HMHZ' 'IRIG'], \
        'shape invalid parameter'
        self.set("SOUR2:FUNC {0}".format(shape))

    def ReadSource2Function(self):
        return self.query("SOUR2:FUNC?")

    def Source3Function(self, shape):
        """
        Sets the function for the Pulse output.
        Manual p.114
        """
        assert shape in ['PULS', 'IRIG'], 'shape paremter invalid'
        self.set("SOUR3:FUNC {0}".format(shape))

    def ReadSource3Function(self):
        return self.query("SOUR3:FUNC?")

    def SourceVoltage(self, voltage, output):
        """
        Sets the AC voltage level for the output to <voltage> or the
        selected limit.
        Manual p.118
        """
        self.ValidateOutput(output)
        self.set("SOUR{0}:VOLT {1}".format(output, voltage))

    def ReadSourceVoltage(self, output):
        self.ValidateSourceOutput(output)
        return self.query("SOUR{0}:VOLT?".format(output))

    def SourceVoltageUnits(self, output, unit):
        """
        Selects the default units when specifying or querying AC
        voltage levels with the command SOUR:VOLT.
        Manual p.118
        """
        self.ValidateSourceOutput(output)
        assert output in [1,2], 'output invalid value'
        assert unit in ['VPP', 'VRMS', "DBM"]
        self.set("SOUR{0}:VOLT:UNIT {1}".format(output, unit))

    def ReadSourceVoltageUnits(self, output):
        self.ValidateSourceOutput(output)
        return self.query("SOUR{0}:VOLT:UNIT?".format(output))

    #################################################################
    ##########  Status Subsystem                           ##########
    #################################################################

    """
    Not implemented:
        STATus:GPS:ENABle
        STATus:OPERation:ENABle
        STATus:QUEStionable:ENABle
    """

    def StatusGPSCondition(self):
        """
        Query the current condition of the GPS receiver.
        Manual p.119
        bit : name
        0 :  Time not set
        1 :  Antenna open
        2 :  Antenna short
        3 :  No satellites
        4 :  UTC unknown
        5 :  Survey in progress
        6 :  No position stored
        7 :  Leap second pending
        8 :
        9 :  Position questionable
        10:
        11:  Almanac incomplete
        12:  No timing pulses
        13:
        14:
        15:
        Manual p.119
        """
        return self.query("STAT:GPS:COND?")

    def StatusGPSEvent(self):
        """
        Query the GPS receiver status event register. Returns all
        bits that have been set since the previous query. The query
        then clears all bits.
        Manual p.120
        """
        return self.query("STAT:GPS:EVEN?")

    def StatusOperationCondition(self):
        """
        Query the current condition of operational status for the
        FS740.
        Manual p.120

        bit : name           : meaning
        0   :                :
        1   : setting        : Hardware instrument settings are
                               changing.
        2   :                :
        3   :                :
        4   : measure front  : Measurement on front input in progress.
        5   : measure rear   : Measurement on rear input in progress.
        6   : event front    : Timing event detected on front input.
        7   : event rear     : Timing event detected on rear input.

        """
        return self.query("STAT:OPER:COND?")

    def StatusOperationEvent(self):
        """
        Query the event register for operational status. This returns
        all bits that have been set since the previous query. The
        query then clears all bits.
        Manual p.120
        """
        return self.query("STAT:OPER:EVEN?")

    def StatusQuestionableCondition(self):
        """
        Query the current condition of questionable status for the
        FS740.
        Manual p.121

        bit : name           : meaning
        0   : time of day    : Instrument time of day has not been
                               set by GPS receiver. Absolute time
                               measurements are invalid.
        1   : warm up        : The timebase is still warming up.
                               Frequency drift will be much larger
                               than normal.
        2   : time unluck    : The timebase is not locked to gps.
                               Time and frequency measurements may be
                               degraded.
        3   :
        4   :
        5   : freq stability : The timebase has not been locked to
                               GPS long enough to reach optimum freq
                               stability.
        6   :
        7   :
        8   :
        9   :
        10  : Rb unlock      : The installed Rb timebase is unlocked.
                               Its frequency is not stable.
        11  : PLL unlock     : One of the internal PLL circuits in
                               in the FS740 has become unlocked. This
                               may signal a need for instrument
                               repair.
        12  : EFC 10MHz      : Indicates that the frequency control
                               of the internal TCXO is near the rail.
        13  : EFC GPS        : Indicates that the frequency control
                               for the installed timebase is
                               saturated. This might indicate a large
                               timing error.
        """
        return self.query("STAT:QUES:COND?")

    def StatusQuestionableEvent(self):
        """
        Query the event register for questionable status. This
        returns all bits that have been set since the previous query.
        The query then clears all bits.
        Manual p.121
        """
        return self.query("STAT:QUES:EVEN?")

    #################################################################
    ##########  System Subsystem                           ##########
    #################################################################

    """
    Not implemented:
        SYSTem:ALARm:FORCe:STATe
        SYSTem:TIMe:LOFFset
    """

    def SystemAlarm(self):
        """
        Query the current state of the system alarm. The FS740 will
        return 1 if the alarm is asserted, otherwise 0.
        Manual p.122
        """
        return self.query("SYST:ALAR?")

    def SystemAlarmClear(self):
        """
        Clear the event register for the system alarm.
        Manual p.122
        """
        self.set("SYST:ALAR:CLE")

    def SystemAlarmCondition(self):
        """
        Query the condition register for the system alarm.
        Manual p.122
        """
        return self.query("SYST:ALAR:COND?")

    def SystemAlarmEnable(self, mask):
        """
        Mask possible alarm conditions so that only those that are
        enabled here can cause the system alarm to be asserted.
        When the current mode for command SYST:ALARm:MODe is TRACk,
        this register masks the condition register for the system alarm,
        SYST:ALARm:CONDition. When the current mode for command
        SYST:ALARm:MODe is LATCh, this register masks the event
        register for the system alarm, SYST:ALARm:EVENt
        Manual p.123
        """
        self.write("SYST:ALAR:ENAB {0}".format(mask))

    def ReadSystemAlarmEnable(self):
        return self.query("SYST:ALAR:ENAB")

    def SystemAlarmEvent(self):
        """
        Query the event register for the system alarm. This
        register indicates which of the possible alarm conditions
        that have been latched since the last time the event
        register was cleared. When the current mode for command
        SYST:ALARm:MODe is LATCh the system alarm will be asserted
        if an event condition is true AND it is enabled in the
        enable register. Note that unlike the event registers in
        the Status Subsystem, reading this register does not clear
        it. It must be explicitly cleared with the
        SYSTem:ALARm:CLEar command.
        Manual p.123
        """
        return self.query("SYS:ALAR:EVEN?")

    def SystemAlarmMode(self, mode):
        """
        Sets the alarm mode to one of three options: track, latch,
        or force.
        Tracking mode causes the alarm to follow current conditions.
        The alarm is asserted when current limits are exceeded. The
        alarm is de-asserted when current limits are no longer
        exceeded.
        Latching mode causes the alarm to be asserted when current
        limits are exceeded. However, the alarm will not be
        de-asserted until explicitly requested to do so and the
        limit is no longer exceeded.
        In force mode, the user manually sets the state of the alarm.
        Manual p.124
        """
        assert mode in ['TRAC', 'LATC', 'FORC'], 'mode invalid value'
        self.write("SYST:ALAR:MOD {0}".format(mode))

    def ReadSystemAlarmMode(self):
        return self.query("SYST:ALAR:MOD?")

    @staticmethod
    def ValidateInterval(interval):
        if self.ValidateMinDefMax(interval):
            return
        else:
            assert (type(interval) == int) or (type(interval) == float), \
            'interval invalid type'
            assert (interval > 5e-8) and (interval <= 1),\
            'interval out of range'
            return

    def SystemAlarmGPSTInterval(self, interval):
        """
        Sets the time interval between GPS and the internal timebase
        that must be exceeded before the alarm condition for a timing
        error is asserted. The <time error> may range from 50 ns to 1
        s. The default is 100 ns.
        Manual p.124
        """
        self.ValidateInterval(interval)
        self.write("SYST:ALAR:TINT {0}".format(interval))

    def ReadSystemAlarmGPSTInterval(self):
        return self.query("SYST:ALAR:TINT")

    @staticmethod
    def ValidateDuration(duration):
        if self.ValidateMinDefMax(duration):
            return
        else:
            assert (type(duration) == int) or\
            (type(duration) == float), \
            'duration invalid type'
            assert (duration > 0), 'duration out of range'
            return

    def SystemAlarmHoldoverDuration(self, duration):
        """
        Sets the amount of time in seconds that the FS740 must be
        in holdover before the alarm condition for holdover is
        asserted. The <duration> may be any 32 bit unsigned integer.
        The default is 0.
        Manual p.124
        """
        self.ValidateDuration(duration)
        self.write("SYST:ALAR:HOLD:DUR {0}")

    def ReadSystemAlarmHoldoverDuration(self):
        self.query("SYST:ALAR:HOLD:DUR?")

    def SystemCommunicateLan(self):
        """
        Query whether the FS740 is connected to the Ethernet LAN.
        The query returns 1 if connected, otherwise 0.
        Manual p.125
        """
        return self.query("SYST:COMM:LAN?")

    def SystemCommunicateLanSpeed(self, speed = '100BASTET'):
        """
        Configures the speed of the Ethernet network to which the
        FS740 is connected, 10BaseT or 100BaseT. If omitted the
        command defaults to 100BaseT. Note that changes to this
        configuration do not take effect until the LAN is reset
        via a SYSTem:COMMunicate:LAN:RESet command or the power
        is cycled.
        Manual p.125
        """
        assert speed in ['10BASET', '100BASET'], \
        'speed invalid parameter value'
        self.write("SYST:COMM:LAN:SPE {0}".format(speed))

    def ReadSystemCommunicateLanSpeed(self):
        """
        Manual p.125
        """
        return self.query("SYST:COMM:LAN:SPE?")

    def SystemCommunicateLanDHCP(self, DHCP = True):
        """
        Enables or disables DHCP for configuring the TCP/IP address
        of the FS740. Note that the new configuration does not take
        effect until the LAN is reset via a
        SYSTem:COMMunicate:LAN:RESet command or the power is cycled.
        Manual p.125
        """
        self.write("SYST:COMM:LAN:DHCP {0}".format(
            'ON' if DHCP else 'OFF'))

    def ReadSystemCommunicateLanDHCP(self):
        return self.query("SYST:COMM:LAN:DHCP?")

    def SystemCommunicateLanGateway(self, gateway):
        """
        Sets the IP address of the gateway or router on the users
        TCP/IP network to be used in static configurations.
        The <ip address> should be specified as a string in the form
        “xxx.xxx.xxx.xxx” where each xxx is replaced by an integer in
        the range from 0 to 255.
        Manual p.126
        """
        self.write("SYST:COMM:LAN:GAT {0}".format(gateway))

    def ReadSystemCommunicateLanGateway(self, option = 'CURR'):
        """
        Accepts 'CURR'ent and 'STAT'ic options.
        Manual p.126
        """
        assert option in ['CURR', 'STAT'], \
        "option invalid parameter value"
        return self.query("SYST:COMM:LAN:GAT? {0}")

    def SystemCommunicateLanIPAddress(self, ip):
        """
        Sets the IP address of the FS740 on the users TCP/IP network
        to be used in static configurations.
        The <ip address> should be specified as a string in the form
        “xxx.xxx.xxx.xxx” where each xxx is replaced by an integer in
        the range from 0 to 255.
        Manual p.126
        """
        self.write("SYST:COMM:LAN:IPAD {0}".format(ip))

    def ReadSystemCommunicateLanIPAddress(self, option = 'CURR'):
        """
        Accepts 'CURR'ent and 'STAT'ic options.
        Manual p.126
        """
        assert option in ['CURR', 'STAT'], \
        'option invalid parameter value'
        return self.query("SYST:COMM:LAN:IPAD? {0}")

    def SystemCommunicateLanSMask(self, smask):
        """
        Sets the subnet mask for the users TCP/IP network to be used
        in static configurations.
        The <ip address> should be specified as a string in the form
        “xxx.xxx.xxx.xxx” where each xxx is replaced by an integer in
        the range from 0 to 255.
        Manual p.127
        """
        self.write("SYST:COMM:LAN:SMAS {0}".format(smask))

    def ReadSystemCommunicateLanSMask(self, option = 'CURR'):
        """
        Accepts 'CURR'ent and 'STAT'ic options.
        Manual p.127
        """
        assert option in ['CURR', 'STAT'], \
        'option invalid parameter value'
        return self.query("SYST:COMM:LAN:SMAS? {0}")

    def SystemCommunicateLanReset(self):
        """
        """
        self.write("SYST:COMM:LAN:RESET")

    def SystemCommunicateSerialBAUD(self, baud):
        """
        Configures the RS-232 port to operate at the selected baud
        rate. Note that the new configuration does not take effect
        until the port is reset via a SYSTem:COMMunicate:SERial:RESet
        command or the power is cycled.
        Manual p.127
        """
        assert baud in [4800, 9600, 19200, 38400, 157600, 115200],\
        'baud rate invalid'
        self.write("SYST:COMM:SER:BAUD {0}".format(baud))

    def ReadSytemCommunicateSerialBaud(self):
        self.query("SYST:COMM:SER:BAUD?")

    def SystemCommunicateSerialReset(self):
        """
        Reset the serial port and activate it using the current
        configured baud rate.
        Manual p.128
        """
        self.write("SYST:COMM:SER:BAUD:RESET")

    def SystemCommunicateLock(self):
        """
        Request an exclusive lock on communication with the FS740.
        The FS740 will return 1 if the request is granted, otherwise
        0. When an interface has an exclusive lock on communication
        with the FS740, other remote interfaces as well as the front
        panel are prevented from changing the instrument state. The
        user should call the command SYSTem:COMMunicate:UNLock command
        to release the exclusive lock when it is no longer needed.
        Manual p.128
        """
        return self.query("SYST:COMM:LOCK?")

    def SystemCommunicateUnlock(self):
        """
        Release an exclusive lock on communication with the FS740 that
        was previously granted with the SYSTem:COMMunicate:LOCK command.
        The FS740 will return 1 if the lock was released, otherwise 0.
        Manual p.128
        """
        return self.query("SYST:COMM:UNL")

    @staticmethod
    def ValidateInt(value, name):
        assert type(value) == int, \
        '{0} not int'.format(name)

    def SystemDate(self, year, month, day):
        """
        Sets the FS740 date if it has not been set by GPS. If the date
        has already been set by GPS, error −221, “Settings conflict,” will
        be generated and the requested date ignored.
        Manual p.129
        """
        self.ValidateInt(year, 'year')
        self.ValidateInt(month, 'month')
        self.ValidateInt(day, 'day')
        assert (month >= 1) and (month <= 12), 'month out of range'
        assert (day >= 1) and (day <= 31), 'day out of range'
        self.write("SYST:DATE {0}, {1}, {2}".format(year, month, day))

    def ReadSystemDate(self):
        return self.query("SYST:DAT?")

    def SystemDisplayPower(self, period):
        """
        Sets the period of inactivity, after which the display is powered
        down.
        Manual p.129
        """
        assert period in ['NOW', 'TMIN', 'OHR', 'THR', 'ODAY', 'NEV'], \
        'period parameter invalid'
        self.write("SYST:DISP:POW {0}".format(period))

    def ReadSystemDisplayPower(self):
        return self.query("SYST:DISP:POW?")

    def SystemDisplayScreen(self, screen):
        """
        Sets the display.
        Manual p.130
        """
        assert screen in ['TBAS', 'GPS', 'COMM', 'SYST', 'SIN',
                          'AUX', 'PULS', 'MEAS1', 'MEAS2'], \
        'screen invalid value'
        self.set("SYST:DISP:SCR {0}".format(screen))

    def ReadSystemDisplayScreen(self):
        return self.query("SYST:DISP:SCR?")

    def SystemError(self):
        """
        Query the next error at the front of the error queue and
        then remove it.
        Manual p.130
        """
        return self.query("SYST:ERR?")

    def SystemSecurityImmediate(self):
        """
        This command wipes the instrument of user settings and
        restores the unit to factory default settings.
        Manual p.130
        """
        self.set("SYST:SEC:IMM")

    def SystemTime(self, hour, minute, second):
        """
        Sets the FS740 time of day if it has not been set by GPS.
        If the time has already been set by GPS, error −221,
        “Settings conflict,” will be generated and the requested time
        ignored. The second definition queries the current time of day.
        It returns the hour, minute, and second as a comma ( , )
        separated list of integers. The second field will be returned
        as a decimal fraction with 10 ns of resolution representing
        the precise time that the query was executed.
        Manual p.131
        """
        self.ValidateInt(hour, 'hour')
        self.ValidateInt(minute, 'minute')
        self.ValidateInt(second, 'second')
        assert (hour >= 0) and (hour <= 23), 'hour out of range'
        assert (minute >= 0) and (minute <= 59), \
        'minute out of range'
        assert (second >= 0) and (second <= 59), \
        'second out of range'
        self.write("SYST:TIM {0}, {1}, {2}".format(hour, minute,
                                                   second))

    def ReadSystemTime(self):
        return self.query("SYST:TIM?")

    def SystemTimePoweron(self):
        """
        Query the date and time at which the FS740 was powered on.
        Manual p.131
        """
        return self.query("SYST:TIM:POW?")



    #################################################################
    ##########  Timebase Subsystem                         ##########
    #################################################################

    """
    Not implemented:
        TBASe:CONFig:BWIDth
        TBASe:CONFig:HMODe
        TBASe:CONFig:LOCK
        TBASe:CONFig:TINTerval:LIMit
        TBASe:EVENt:CLEar
        TBASe:FCONtrol
        TBASe:FCONtrol:SAVe
        TBASe:TCONstant
    """

    def TBaseEventNext(self):
        """
        Query the queue of timebase events for the next event.
        Manual p.134

        event : name
        =========================
        NON   : None
        POW   : Power up
        UNL   : Unlock
        SEAR  : Searching for GPS
        STAB  : Stabilizing
        VTIME : Validate time
        LOCK  : Lock
        MAN   : Manual holdover
        NGPS  : No GPS
        BGPS  : Bad GPS
        """
        return self.query("TBAS:EVEN?")

    def TBaseState(self):
        """
        Query the current state of the timebase.
        Manual p.135

        state : meaning
        ======================================
        POW   : Powered up recently
        SEAR  : Searching for GPS
        STAB  : Stabilizing timebase frequency
        VTIME : Validating GPS time of day
        LOCK  : Locked to GPS
        MAN   : Holdover at user request
        NGPS  : No GPS, in holdover
        BGPS  : Bad GPS, in holdover
        UNL   : Rb oscillator unlocked
        """
        return self.query("TBAS?")

    def TBaseStateHoldoverDuration(self):
        """
        Query the length of time in secondsthe FS740 has been in
        holdover.
        Manual p.136
        """
        return self.query("TBAS:STAT:HOLD:DUR?")

    def TBaseStateLockDuration(self):
        """
        Query the length of time in seconds the FS740 has been locked
        to GPS.
        Manual p.136
        """
        return self.query("TBAS:STAT:LOCK:DUR?")

    def TBaseStateWarumpDuration(self):
        """
        Query the time in seconds that passed between when the FS740
        was powered on and it first locked to GPS.
        Manual p.136
        """
        return self.query("TBAS:WARM?")

    def TBaseTConstant(self, loop_time_constant = 'CURR'):
        """
        Query the the loop time constant; either CURRent, TARGet or MANual.
        Manual p.136
        """
        assert loop_time_constant in ['CURR', 'TARG', 'MAN'], \
        'loopt TC invalid parameter value'
        return self.query("TBAS:TCON? {0}".format(loop_time_constant))

    def TBaseTInterval(self, average = False):
        """
        Query the current or average measured time interval in
        seconds between the internal timebase and GPS.
        Manual p.137
        """
        return self.query("TBASE:TINT? {0}".format(
            'AVER' if average else 'CURR'))

    #################################################################
    ##########  Trigger Subsystem                          ##########
    #################################################################
    """
    Commands in the Trigger Subsystem control the triggering of
    measurements. Normally when under local control, measurements are
    triggered continuously in order to provide continuous feedback
    while interacting with the instrument. Conversely, under remote
    control, measurements are only triggered when requested so that
    the data displayed corresponds closely with data retrieved.
    Commands in this subsystem enable the user to alter this behavior.
    """

    def TriggerContinuous(self, on = True):
        """
        Sets the desired trigger mode.
        Manual p.137Z
        """
        self.set("TRIG:CONT {0}".format('ON' if on else 'OFF'))

    def ReadTriggerContinuous(self):
        return self.query("TRIG:CONT?")
