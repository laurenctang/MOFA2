from __future__ import division
import numpy.ma as ma
import numpy as np
import scipy as s
import scipy.special as special

from biofam.core.utils import dotd

# Import manually defined functions
from .variational_nodes import Gamma_Unobserved_Variational_Node

from biofam.core.distributions import *


class TauD_Node(Gamma_Unobserved_Variational_Node):
    def __init__(self, dim, pa, pb, qa, qb, qE=None):
        super().__init__(dim=dim, pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
        self.precompute()

    def precompute(self):
        self.N = self.dim[0]
        self.lbconst = s.sum(self.P.params['a'][0,:]*s.log(self.P.params['b'][0,:]) - special.gammaln(self.P.params['a'][0,:]))

    # def getExpectations(self, expand=True):
    #     QExp = self.Q.getExpectations()
    #     if expand:
    #         D = self.markov_blanket['SW'].D
    #         expanded_E = s.repeat(QExp['E'][None, :], D, axis=0)
    #         expanded_lnE = s.repeat(QExp['E'][None, :], D, axis=0)
    #         return {'E': expanded_E, 'lnE': expanded_lnE}
    #     else:
    #         return QExp
    #
    # def getExpectation(self, expand=True):
    #     QExp = self.getExpectations(expand)
    #     return QExp['E']

    def updateParameters(self):

        # Collect expectations from other nodes
        Y = self.markov_blanket["Y"].getExpectation().copy()
        mask = ma.getmask(Y)

        if "SW" in self.markov_blanket:
            Wtmp = self.markov_blanket["SW"].getExpectations()
            Ztmp = self.markov_blanket["Z"].getExpectations()
        else:
            Wtmp = self.markov_blanket["W"].getExpectations()
            Ztmp = self.markov_blanket["SZ"].getExpectations()
        W, WW = Wtmp["E"], Wtmp["E2"]
        Z, ZZ = Ztmp["E"], Ztmp["E2"]

        # Collect parameters from the P and Q distributions of this node
        P, Q = self.P.getParameters(), self.Q.getParameters()
        Pa, Pb = P['a'], P['b']

        # Mask matrices
        Y = Y.data
        Y[mask] = 0.

        # Calculate terms for the update
        # term1 = s.square(Y).sum(axis=0).data # not checked numerically with or without mask
        term1 = s.square(Y.astype("float64")).sum(axis=0)

        # term2 = 2.*(Y*s.dot(Z,W.T)).sum(axis=0).data
        term2 = 2.*(Y*s.dot(Z,W.T)).sum(axis=0) # save to modify


        term3 = ma.array(ZZ.dot(WW.T), mask=mask).sum(axis=0)

#<<<<<<< HEAD
#        # dotd(SWZ, SWZ.T) should compute a sum for all k and k' of W_{d,k} Z_{d,k} W_{d,k'} Z_{d,k'} including for k=k', and then summed over n
#        # s.dot(s.square(Z),s.square(SW).T) computes the sum over all k of wdk^2 * znk2 summed over all n too
#        term4 = dotd(SWZ, SWZ.T) - ma.array(s.dot(s.square(Z),s.square(SW).T), mask=mask).sum(axis=0)
#=======
        WZ = ma.array(W.dot(Z.T), mask=mask.T)
        term4 = dotd(WZ, WZ.T) - ma.array(s.dot(s.square(Z),s.square(W).T), mask=mask).sum(axis=0)

        tmp = term1 - term2 + term3 + term4

        # Perform updates of the Q distribution
        Qa = Pa + s.repeat((Y.shape[0] - mask.sum(axis=0))[None,:], self.N, axis=0)/2.
        Qb = Pb + s.repeat(tmp.copy()[None,:], self.N, axis=0)/2.

        # Save updated parameters of the Q distribution
        self.Q.setParameters(a=Qa, b=Qb)

    def calculateELBO(self):
        # Collect parameters and expectations from current node
        P, Q = self.P.getParameters(), self.Q.getParameters()
        Pa, Pb, Qa, Qb = P['a'][0,:], P['b'][0,:], Q['a'][0,:], Q['b'][0,:]
        QE, QlnE = self.Q.expectations['E'][0,:], self.Q.expectations['lnE'][0,:]

        # Do the calculations
        lb_p = self.lbconst + s.sum((Pa-1.)*QlnE) - s.sum(Pb*QE)
        lb_q = s.sum(Qa*s.log(Qb)) + s.sum((Qa-1.)*QlnE) - s.sum(Qb*QE) - s.sum(special.gammaln(Qa))

        return lb_p - lb_q

    def sample(self, distrib='P'):
        #instead of overwriting sample, we should maybe change the dimensions of this node !
        P = Gamma(dim=(self.dim[1],1), a=self.P.params["a"][0,:], b=self.P.params["b"][0,:])
        self.samp = P.sample()
        return self.samp


class TauN_Node(Gamma_Unobserved_Variational_Node):
    def __init__(self, dim, pa, pb, qa, qb, qE=None):
        super().__init__(dim=dim, pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
        self.precompute()

    def precompute(self):
        self.D = self.dim[1]
        self.lbconst = s.sum(self.P.params['a'][:,0]*s.log(self.P.params['b'][:,0]) - special.gammaln(self.P.params['a'][:,0]))

    def updateParameters(self):
        # Collect expectations from other nodes
        Y = self.markov_blanket["Y"].getExpectation().copy()
        mask = ma.getmask(Y)

        if "SW" in self.markov_blanket:
            Wtmp = self.markov_blanket["SW"].getExpectations()
            Ztmp = self.markov_blanket["Z"].getExpectations()
        else:
            Wtmp = self.markov_blanket["W"].getExpectations()
            Ztmp = self.markov_blanket["SZ"].getExpectations()
        W, WW = Wtmp["E"], Wtmp["E2"]
        Z, ZZ = Ztmp["E"], Ztmp["E2"]

        # Collect parameters from the P and Q distributions of this node
        P, Q = self.P.getParameters(), self.Q.getParameters()
        Pa, Pb = P['a'], P['b']

        # Mask matrices
        Y = Y.data
        Y[mask] = 0.

        # Calculate terms for the update
        term1 = s.square(Y.astype("float64")).sum(axis=1)

        term2 = 2.*(Y*s.dot(Z,W.T)).sum(axis=1) # save to modify

        term3 = ma.array(ZZ.dot(WW.T), mask=mask).sum(axis=1)

        ZW = ma.array(Z.dot(W.T), mask=mask)
        term4 = dotd(ZW, ZW.T) - ma.array(s.dot(s.square(Z), s.square(W).T), mask=mask).sum(axis=1)

        tmp = term1 - term2 + term3 + term4

        # Perform updates of the Q distribution
        Qa = Pa + s.repeat((Y.shape[1] - mask.sum(axis=1))[:,None], self.D, axis=1)/2.
        Qb = Pb + s.repeat(tmp.copy()[:,None], self.D, axis=1)/2.

        # Save updated parameters of the Q distribution
        self.Q.setParameters(a=Qa, b=Qb)

    def calculateELBO(self):
        # Collect parameters and expectations from current node
	# older version of the code before biofam2
#<<<<<<< HEAD
#        P,Q = self.P.getParameters(), self.Q.getParameters()
#        Pa, Pb, Qa, Qb = P['a'], P['b'], Q['a'], Q['b']
#        QE, QlnE = self.Q.expectations['E'], self.Q.expectations['lnE']
#=======
        P, Q = self.P.getParameters(), self.Q.getParameters()
        Pa, Pb, Qa, Qb = P['a'][:,0], P['b'][:,0], Q['a'][:,0], Q['b'][:,0]
        QE, QlnE = self.Q.expectations['E'][:,0], self.Q.expectations['lnE'][:,0]

        # Do the calculations
        lb_p = self.lbconst + s.sum((Pa-1.)*QlnE) - s.sum(Pb*QE)
        lb_q = s.sum(Qa*s.log(Qb)) + s.sum((Qa-1.)*QlnE) - s.sum(Qb*QE) - s.sum(special.gammaln(Qa))

        return lb_p - lb_q

    def sample(self, distrib='P'):
        #instead of overwriting sample, we should maybe change the dimensions of this node
        P = Gamma(dim=(self.dim[0], 1), a=self.P.params["a"][:,0], b=self.P.params["b"][:,0])
        self.samp = P.sample()
        return self.samp