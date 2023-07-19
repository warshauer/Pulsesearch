
import time
# class to interpret scans

class scan()
    def __init__(self, movingAxis = 0, startPosition = {0:0,1:0,2:0}):
        
        self.x = []
        self.y = [[]]

    def runtime_function(self):
        # check whether to append data:
        if self.started:
            if self.esp.moving() == False and self.stageJustMoved == True:
                self.timeStageEnd = time.monotonic()
                self.stageJustMoved = False
            elif self.esp.moving() == False and self.stageJustMoved == False:
                if time.monotonic() - self.timeStageEnd > 2.1*max(self.timeConstants):#1.4*max(self.timeConstants):
                    self.appendData()
                    self.updatePlot()
                    #self._threadWork(self.updatePlot)
                    #self.cutie.run()
                    if self.moveOn == False:
                        self._moveStep()
                    else:
                        self._moveToStartPositions(delay = self.delay)
                        self._update_scan_numbers()
                        self.x = []
                        self.y[1]['live'] = []
                        self.y[2]['live'] = []
                        self.moveOn = False
        self._update_stage_positions()
        self._update_stage_values()

    def scanRuntime(self, moving):
        if moving == False and self.stageJustMoved == True:
            self.timeStageEnd = time.monotonic()
            self.stageJustMoved = False
        elif moving == False and self.stageJustMoved == False:
            if time.monotonic() - self.timeStageEnd > 2.1*max(self.timeConstants):#1.4*max(self.timeConstants):
                self.appendData()
                self.updatePlot()
                #self._threadWork(self.updatePlot)
                #self.cutie.run()
                if self.moveOn == False:
                    self._moveStep()
                else:
                    self._moveToStartPositions(delay = self.delay)
                    self._update_scan_numbers()
                    self.x = []
                    self.y[1]['live'] = []
                    self.y[2]['live'] = []
                    self.moveOn = False



# proceed has three states:
# 1 - move
# 2 - wait
# 3 - log

    def proceed(self):
        if self.esp.moving() == False and self.stageJustMoved == True:
            self.timeStageEnd = time.monotonic()
            self.stageJustMoved = False
        elif self.esp.moving() == False and self.stageJustMoved == False:
            if time.monotonic() - self.timeStageEnd > 2.1*max(self.timeConstants):
                self.appendData()
                self.updatePlot()
                self.runNextCommand()
                else:
                    self._moveToStartPositions(delay = self.delay)
                    self._update_scan_numbers()
                    self.x = []
                    self.y[1]['live'] = []
                    self.y[2]['live'] = []
                    self.moveOn = False

    def runNextCommand():
        if len(self.commands) > 0:
            for func in self.commands.pop(0):
                func()
        else:
            newScan()


        

    def initializeScan(*args, numSteps = 3):
        # arg = {'index':stageIndex, 'start':startPosition, 'moving':True/False, 'stepsize':stepSize}
        movingIndices = []
        movingStepsizes = []
        startCommands = []
        for arg in args:
            index = arg['index']
            startPosition = arg['startPosition']
            startCommands.append(lambda:self.esp.move_to_position(index, startPosition))
            if arg['moving']:
                movingIndices.append(index)
                movingStepsizes.append(arg['stepsize'])
        self.commands = []
        self.commands.append(startCommands)
        for j in range(numSteps):
            moveCommand = []
            for i in range(len(movingIndices)):
                moveCommand.append(lambda:self.esp.move_step(movingIndices[i], movingStepsizes[i]*.001))
            self.commands.append(moveCommand)
        



        
