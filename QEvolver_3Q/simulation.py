# -*- coding: utf-8 -*-
"""
@author: Fei Yan
"""


from scipy.linalg import eig
from qutip import *

# import scipy.constants as const
# #Constants.
# h = const.h #planck constant
# h_bar = const.hbar #h_bar
# e = const.e #electron charge
# phi0= h/(2*e) #flux quantum
# RQ = h/(2*e)**2 #quantum resistance

List_sPauli = ['I','X','Y','Z']
List_mPauli = [qeye(2), sigmax(), sigmay(), sigmaz()]


def U(H,t):
	# unitary propagator generated by H over time t 
	H = Qobj(H)
	return Qobj(-1j * H * t).expm()

def T(A, U):
	A = Qobj(A)
	U = Qobj(U)
	return U * A * U.dag()

def Qflatten(Q):
	return Qobj(Q.full())

def eigensolve(H):
	# find eigensolution of H
	H = H.full()
	vals, vecs = eig(H)    
	#idx = vals.argsort()[::-1] #Descending Order
	idx = vals.argsort() #Ascending Order
	vals = vals[idx]
	vecs = vecs[:,idx]
	return np.real(vals), vecs

def level_identify(vals, vecs, list_table, list_select):
	# identify and sort eigen solutions according to "list_select"
	v_idx = []
	for k, str_level in enumerate(list_select):
		idx_sort = np.argsort(np.abs(vecs[list_table.index(str_level),:]))
		count = 1
		while True:
			if idx_sort[-count] in v_idx:
				count += 1
			else:
				v_idx.append(idx_sort[-count])
				break			
	return vals[v_idx], vecs[:,v_idx]

def generateBasicOperator(nTrunc):
	# generate basic operators. matrix truncated at nTrunc 
	I = qeye(nTrunc)
	a = destroy(nTrunc)
	x = a + a.dag()
	p = -1j*(a - a.dag())
	aa = a.dag() * a
	aaaa = a.dag() * a.dag() * a * a
	return {'I':I, 'a':a, 'x':x, 'p':p, 'aa':aa, 'aaaa':aaaa}



class simulation_3Q():

	def __init__(self, CONFIG):
		# init with some default settings
		self.nQubit = int(CONFIG.get('Number of Qubits')),
		self.nTrunc = int(CONFIG.get('Degree of Trunction'))
		self.dTimeStart = CONFIG.get('Time Start')
		self.dTimeEnd = CONFIG.get('Time End')
		self.nTimeList = int(CONFIG.get('Number of Samples'))
		self.tlist = np.linspace(self.dTimeStart, self.dTimeEnd, self.nTimeList)
		self.dt = self.tlist[1] - self.tlist[0]	
		# self.nShow = 4

		# generate qubit idling config.
		for sQubit in List_sQubit:
			sName = 'qubitCfg_' + sQubit
			setattr(self, sName, QubitConfiguration(sQubit, CONFIG))
		# generate capacitance network config.
		self.capCfg = CapacitanceConfiguration(CONFIG)

		self.a00 = CONFIG.get('a00')
		self.a01 = CONFIG.get('a01')
		self.a10 = CONFIG.get('a10')
		self.a11 = CONFIG.get('a11')
		self.psi_input_logic = Qobj(np.array([self.a00,self.a01,self.a10,self.a11])).unit()
		self.rho_input_logic = self.psi_input_logic * self.psi_input_logic.dag()

		self.T1_Q1 = CONFIG.get('Q1 T1')
		self.Gamma1_Q1 = 1/self.T1_Q1
		self.T1_Q2 = CONFIG.get('Q2 T1')
		self.Gamma1_Q2 = 1/self.T1_Q2
		self.T1_Q3 = CONFIG.get('Q3 T1')
		self.Gamma1_Q3 = 1/self.T1_Q3


	def updateSequence(self, sequence):
		# input sequence
		for sQubit in List_sQubit:
			for sSeqType in List_sSeqType:
				sName = 'timeFunc_' + sQubit + '_' + sSeqType
				setattr(self, sName, getattr(sequence, sName))


	def generateSubHamiltonian_3Q(self):
		# generate partial Hamiltonian in 3-qubit system
		OP = generateBasicOperator(self.nTrunc)
		self.OP = OP
		# self Hamiltonian operators
		self.H_Q1_aa = Qflatten(tensor(OP['aa'], OP['I'], OP['I']))
		self.H_Q1_aaaa = Qflatten(tensor(OP['aaaa'], OP['I'], OP['I']))
		self.H_Q2_aa = Qflatten(tensor(OP['I'], OP['aa'], OP['I']))
		self.H_Q2_aaaa = Qflatten(tensor(OP['I'], OP['aaaa'], OP['I']))
		self.H_Q3_aa = Qflatten(tensor(OP['I'], OP['I'], OP['aa']))
		self.H_Q3_aaaa = Qflatten(tensor(OP['I'], OP['I'], OP['aaaa']))
		# coupling Hamiltonian operators
		self.H_g12_xx = Qflatten(tensor(OP['x'], OP['x'], OP['I']))
		self.H_g23_xx = Qflatten(tensor(OP['I'], OP['x'], OP['x']))
		self.H_g13_xx = Qflatten(tensor(OP['x'], OP['I'], OP['x']))		#
		self.H_g12_pp = Qflatten(tensor(OP['p'], OP['p'], OP['I']))
		self.H_g23_pp = Qflatten(tensor(OP['I'], OP['p'], OP['p']))
		self.H_g13_pp = Qflatten(tensor(OP['p'], OP['I'], OP['p']))
		# drive Hamiltonian operators
		self.H_Q1_dr_x = Qflatten(tensor(OP['x'], OP['I'], OP['I']))
		self.H_Q2_dr_x = Qflatten(tensor(OP['I'], OP['x'], OP['I']))
		self.H_Q3_dr_x = Qflatten(tensor(OP['I'], OP['I'], OP['x']))
		self.H_Q1_dr_p = Qflatten(tensor(OP['p'], OP['I'], OP['I']))
		self.H_Q2_dr_p = Qflatten(tensor(OP['I'], OP['p'], OP['I']))
		self.H_Q3_dr_p = Qflatten(tensor(OP['I'], OP['I'], OP['p']))
		# collapse operators
		self.L_Q1_a = Qflatten(tensor(OP['a'], OP['I'], OP['I']))
		self.L_Q2_a = Qflatten(tensor(OP['I'], OP['a'], OP['I']))
		self.L_Q3_a = Qflatten(tensor(OP['I'], OP['I'], OP['a']))


	def generateHamiltonian_3Q_cap(self):
		# # construct 3-qubit Hamiltonian
		# self.generateSubHamiltonian_3Q()
		# self Hamiltonian
		self.H_Q1 = self.qubitCfg_Q1.Frequency * self.H_Q1_aa + self.qubitCfg_Q1.Anharmonicity/2 * self.H_Q1_aaaa
		self.H_Q2 = self.qubitCfg_Q2.Frequency * self.H_Q2_aa + self.qubitCfg_Q2.Anharmonicity/2 * self.H_Q2_aaaa
		self.H_Q3 = self.qubitCfg_Q3.Frequency * self.H_Q3_aa + self.qubitCfg_Q3.Anharmonicity/2 * self.H_Q3_aaaa
		# coupling Hamiltonian
		self.g12_pp = 0.5 * self.capCfg.r12 * np.sqrt(self.qubitCfg_Q1.Frequency * self.qubitCfg_Q2.Frequency)
		self.H_12 = self.g12_pp * self.H_g12_pp
		self.g23_pp = 0.5 * self.capCfg.r23 * np.sqrt(self.qubitCfg_Q2.Frequency * self.qubitCfg_Q3.Frequency)
		self.H_23 = self.g23_pp * self.H_g23_pp
		self.g13_pp = 0.5 * self.capCfg.r13 * np.sqrt(self.qubitCfg_Q1.Frequency * self.qubitCfg_Q3.Frequency)
		self.H_13 = self.g13_pp * self.H_g13_pp
		# system Hamiltonian
		self.H_idle = self.H_Q1 + self.H_Q2 + self.H_Q3 + self.H_12 + self.H_23 + self.H_13


	def generateLabel_3Q(self):
		# generate 3-qubit number state label list
		list_label_gen = [str(n) for n in range(16)]
		self.list_label_table = []
		for k1 in np.arange(self.nTrunc):
			for k2 in np.arange(self.nTrunc):
				for k3 in np.arange(self.nTrunc):
					self.list_label_table.append(list_label_gen[k1] + list_label_gen[k2] + list_label_gen[k3])


	def generateCollapse_3Q(self):
		self.c_ops = [np.sqrt(self.Gamma1_Q1) * L_Q1_a,
					 np.sqrt(self.Gamma1_Q2) * L_Q2_a,
					 np.sqrt(self.Gamma1_Q3) * L_Q3_a]


	def generateInitialState(self):
		#
		self.generateLabel_3Q()
		self.list_label_sub = ["000","001","100","101"]
		self.vals_idle, self.vecs_idle = eigensolve(self.H_idle)
		self.vals_idle_sub, vecs_idle_sub = level_identify(self.vals_idle, self.vecs_idle, self.list_label_table, self.list_label_sub)
		#
		self.U_logic_to_full = Qobj(self.vecs_sub)
		self.U_full_to_logic = self.U_logic_to_full.dag()
		#
		self.rho_input_rot = T(self.rho_input_logic, self.U_logic_to_full)
		self.rho_input_lab = T(self.rho_input_rot, U(self.H_idle, self.tlist[0]))
		self.rho0 = self.rho_input_lab


	def rhoEvolver_3Q(self):
		#
		self.result = mesolve(H=[
			[2*np.pi*self.H_Q1_aa, self.timeFunc_Q1_Frequency],
			[2*np.pi*self.H_Q1_aaaa, self.timeFunc_Q1_Anharmonicity],
			[2*np.pi*self.H_Q2_aa, self.timeFunc_Q2_Frequency],
			[2*np.pi*self.H_Q2_aaaa, self.timeFunc_Q2_Anharmonicity],
			[2*np.pi*self.H_Q3_aa, self.timeFunc_Q3_Frequency],
			[2*np.pi*self.H_Q3_aaaa, self.timeFunc_Q3_Anharmonicity],
			[2*np.pi*self.H_g12_pp, self.timeFunc_g12_pp],
			[2*np.pi*self.H_g23_pp, self.timeFunc_g23_pp],
			[2*np.pi*self.H_g13_pp, self.timeFunc_g13_pp],
			[2*np.pi*self.H_Q1_dr_p, self.timeFunc_Q1_DriveP],
			[2*np.pi*self.H_Q2_dr_p, self.timeFunc_Q2_DriveP],
			[2*np.pi*self.H_Q3_dr_p, self.timeFunc_Q3_DriveP]
			],
			rho0 = self.rho0, tlist = self.tlist, c_ops = self.c_ops, args = [])#, options = options), store_states=True, c_ops=[], e_ops=[]
		# return result.states


	def generateObservables(self):
		sPre = 'Time Series: '
		self.dict_Pauli2 = {}
		self.dict_vStateTomo = {}
		for k1 in range(4):
			for k2 in range(4):
				key = List_sPauli[k1] + List_sPauli[k2]
				self.dict_Pauli2[key] = Qflatten(tensor(List_mPauli[k1], List_mPauli[k2]))
				self.dict_vStateTomo[sPre + key] = []
		#
		for k, t in enumerate(self.tlist):
			rho_lab = self.results.states[k]
			rho_rot = T(rho_lab, U(self.H_idle, t).dag())
			rho_logic = T(rho_rot, U_sub.dag())
			for key, op in self.dict_Pauli2.items():
				self.dict_vStateTomo[sPre + key].append((op * rho_logic).tr())


	def generateSeqDisplay(self):
		#
		sPre = 'Time Series: '
		self.dict_vSeq = {sPreS + s : [] for s in self.lSeq}
		for sQubit in List_sQubit:
			for sSeqType in List_sSeqType:
				sName = sPre + sQubit + ' ' + sSeqType
				sCallName = 'timeFunc_' + sQubit + '_' + sSeqType
				methodToCall = getattr(self, sCallName)
				for t in self.tlist:
					self.dict_vSeq[sName].append(methodToCall(t))
