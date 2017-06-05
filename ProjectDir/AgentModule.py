import MalmoPython as Malmo
from _collections import defaultdict
import random
import CoordinateUtils


qTable_DEFAULT = 0
'''
##################################################################
#--------------------------todo----------------------------------#
##################################################################

##################################################################
#--------------------------\todo---------------------------------#
##################################################################
'''

def createQTable():
    innerDef = lambda: qTable_DEFAULT
    outerDef = lambda: defaultdict(innerDef)
    return defaultdict(outerDef) #qTable[state][action][projectedReward]

class Agent:
    def __init__(self, world, start=(0,0,0), n=1, alpha=1, gamma=1.0, moveCap = 100):

        self.start = start #starting square
        
        self.world = world # keep a reference to the world... TODO: evaluate whether or not this is a good idea
        self.ourAgent = Malmo.AgentHost()
        self.moveCap = moveCap
        
        '''Q Learning'''
        self.n = n #num of states back to update in the qTable
        self.alpha = alpha #learning rate
        self.gamma = gamma #discount factor
        self.qTable = createQTable()
        '''end Q Learning'''
        
        '''episodic variables'''
        self.moveCount = 0
        self.moveHistory = [start] # [locs]... list of the locs we traversed so far...
        self.actionHistory = []
        self.rewardHistory = []
        '''end episodic variables'''

        '''Analytics'''
        self.episodeCount = 0
        self.totalMoveCount = 0
        self.bestScoreSoFar = -999
        self.bestPathSoFar = []

        self.movesPerEpisode = []
        self.rewardScorePerEpisode = []
        self.rewardsCollectedPerEpisode = []
        '''End Analytics'''

    def updateAnalyticsBeforeNewEpisode(self, printInfo=False):
        self.episodeCount += 1

        if self.episodeCount > 1:
            # update move trackers
            self.totalMoveCount += self.moveCount
            self.movesPerEpisode.append(self.moveCount)

            # update reward trackers
            rewardSum = sum(self.rewardHistory)
            self.rewardScorePerEpisode.append(rewardSum)
            self.rewardsCollectedPerEpisode.append(sum(self.world.rewardList))
            if rewardSum > self.bestScoreSoFar:
                self.bestScoreSoFar = rewardSum
                self.bestPathSoFar = self.moveHistory

            if printInfo:
                print "analytics:"
                print " - total moves: " + str(self.totalMoveCount)
                print " - total episodes: " + str(self.episodeCount)
                print " - best score so far: " + str(self.bestScoreSoFar)
                print " - best path so far: " + str(self.bestPathSoFar)
                print " - moves per episode: " + str(self.movesPerEpisode)
                print " - reward score per episode " + str(self.rewardScorePerEpisode)
                print " - rewards collected per epsiode: " + str(self.rewardsCollectedPerEpisode)

    def clearAnalytics(self):
        self.episodeCount = 0
        self.totalMoveCount = 0
        self.bestScoreSoFar = -999
        self.bestPathSoFar = []

        self.movesPerEpisode = []
        self.rewardScorePerEpisode = []
        self.rewardsCollectedPerEpisode = []

    def new_episode(self, verbose = False):
        self.updateAnalyticsBeforeNewEpisode(verbose)
        with open("analytics.csv", "w") as f:
            f.write("episode #\tmoves #\treward score\trewards collected")
            for i in range(self.episodeCount-1):
                f.write("\n" + str(i) + "\t" + str(self.movesPerEpisode[i]) + "\t" + str(self.rewardScorePerEpisode[i]) + "\t" + str(self.rewardsCollectedPerEpisode[i]))
                f.flush()
        self.finishedMaze = False
        self.moveHistory = [self.start]
        self.actionHistory = []
        self.rewardHistory = []
        self.moveCount = 0
        self.world.newEpisode()#TODO: interects with world

    def completeReset(self):
        self.new_episode()
        self.clearAnalytics()
        self.qTable = createQTable()

    def getCurrentState(self):
        #returns (curLoc, itemsLooted)
        return (self.moveHistory[-1], tuple(self.world.rewardList))
    
    def isAlive(self):
        return self.moveCap > self.moveCount and not self.world.onDangerBlock() 
    
    def getRawardTotal(self):
        return sum(self.rewardHistory)
    
    def makeMove(self, eps = .5, verbose = True):
        old_state = (tuple(self.world.rewardList), self.moveHistory[-1])
        possibleMoves = CoordinateUtils.movement2D #hard-coded 2D movement
        moveToTake = self.chooseAction(possibleMoves, eps)
        self.actionHistory.append(moveToTake)
        self.moveHistory.append(CoordinateUtils.sumCoordinates(moveToTake, self.moveHistory[-1]))
        
        reward = self.world.moveAgent(moveToTake)#TODO: interects with world
        if self.world.finishedMaze:
            reward += 10

        self.rewardHistory.append(reward)
        self.moveCount += 1
        """
        if self.moveHistory[-1] in self.world.getRewardList():#TODO: interects with world
            a = self.world.getRewardList().index(self.moveHistory[-1])#TODO: interects with world
            self.rewardsLooted[a] = 1
        """
        self.updateQTable(old_state)
        if verbose:
            self.printStatus()
        
        

    def chooseAction(self, possibleMoves, eps, testing = False):
        if testing:
            #todo: return random move in possibleMoves
            rand = random.randrange(len(possibleMoves))
            return possibleMoves[rand]
        else:
            rnd = random.random()
            if rnd < eps:
                a = random.randint(0, len(possibleMoves) - 1)
                return possibleMoves[a]
            else:
                cur_state = (tuple(self.world.rewardList), self.moveHistory[-1])
                return self._bestMove(possibleMoves, cur_state)

    def printStatus(self):
        print "make move..."
        print " - self.actionHistory = " + str(self.actionHistory)
        print " - self.rewardHistory = " + str(self.rewardHistory)
        print " - self.rewardsLooted = " + str(self.world.rewardList)
        #TODO: commented out due to inconsistancies with worldsim
        #print " - self.world.totalRewards = " + str(self.world.totalRewards)
        #print " - self.world.lastReward = " + str(self.world.lastReward)


    ########################################################################################################
    #-----------------------------------------QTable Code--------------------------------------------------#
    ########################################################################################################
    
    def updateQTable(self, old_state):
        n = self.moveCount if self.moveCount < self.n else self.n
        cur_state = (tuple(self.world.rewardList), self.moveHistory[-1])
        for i in range(-n, 0):
            #for the past n state/action pairs
            G = self.rewardHistory[-1]
            G += self.gamma ** -(i+1) * self._optimalValue(cur_state)
            G-= self.qTable[old_state][self.actionHistory[-1]]
            G*= self.alpha
            self.qTable[old_state][self.actionHistory[-1]] += G
    
    def _optimalValue(self, state):
        possible = [value for _, value in self.qTable[state].items()]
        if len(possible) == 0:
            return 0
        else:
            return max(possible)
    
    def _bestMove(self, possibleMoves, state):
        posBest = []
        bestReward = -10000
        for i, action in enumerate(possibleMoves):
            if self.qTable[state][action] > bestReward:
                bestReward = self.qTable[state][action]
                posBest = [i]
            elif self.qTable[state][action] == bestReward:
                posBest.append(i)
        a = random.randint(0, len(posBest) - 1)
        return possibleMoves[posBest[a]]

