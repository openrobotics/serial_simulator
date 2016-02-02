import struct
'''		while (self.thread_alive):
			if self.serial_rx is not None:
				incoming = self.serial_rx.read(5)
				if incoming is not '':
					packet_formatting = 'BBBBB'
					if len(incoming) == struct.calcsize(packet_formatting):
						print "Packet received: " + incoming
						packet = struct.unpack(packet_formatting, incoming)
						print packet
						print "%.3f" %((packet[4] * 256 + packet[3]) * 5.0/1024)
'''

class DataStructure:
	'''Preliminary structure to hold C struct data for microcontroller network
	'''
	#indices for location of values in dataIn and dataOut lists
	name = 0 
	packing_type = 1
	current_value = 2

	def __init__(self, delimiter):
		self.delimiter = delimiter
		self.dataIn = []
		self.dataOut = []

	def get_input_packet_formatting(self):
		packet_formatting = ''
		for variable in self.dataIn:
			packet_formatting += variable[DataStructure.packing_type]
		return packet_formatting

	def get_input_packet_size(self):
		return struct.calcsize(self.get_input_packet_formatting())

	def get_output_packet_formatting(self):
		packet_formatting = ''
		for variable in self.dataOut:
			packet_formatting += variable[DataStructure.packing_type]
		return packet_formatting

	def get_output_packet_size(self):
		return struct.calcsize(self.get_output_packet_formatting())

	def printOutputPacket(self):
		for variable in self.dataOut:
			print variable

	def set(self, data):
		print 'filling'

	def get(self, data):
		print 'sending'

'''
volatile struct dataIn
{
	uint8_t speed1;
	uint8_t speed2;
	uint8_t status;
} dataIn;

volatile struct dataOut
{
	char output[16];
} dataOut;

'''

v2_drivetrain = DataStructure('@V2DT')
v2_drivetrain.dataIn.append(['speed1', 'B', 0])
v2_drivetrain.dataIn.append(['speed2', 'B', 0])
v2_drivetrain.dataIn.append(['status', 'B', 0])
v2_drivetrain.dataOut.append(['output', 'ccccccccccccccc', 0])

mini_arm = DataStructure('@MARM')
mini_arm.dataIn.append(['status', 'B', 0])
mini_arm.dataOut.append(['analogReadings', 'HHHHHHHH', 0])