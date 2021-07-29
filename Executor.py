import queue
from threading import Thread, Condition


class ThreadPoolExecutor(Thread):

    def __init__(self, max_workers):
        super(ThreadPoolExecutor, self).__init__(name="Thread Pool Executor")

        self.queue = queue.Queue(2 * 1024)
        self.lock = WorkThreadLock(max_workers)
        self.max_workers = max_workers
        self.interrupted = False

        self.setDaemon(True)
        pass

    def add(self, thread: Thread):
        self.queue.put(thread)
        pass

    def isInterrupted(self) -> bool:
        return self.interrupted

    def run(self) -> None:
        while not self.isInterrupted():
            while self.lock.count < self.max_workers:
                thread = self.queue.get()
                self.lock.increase()
                thread.start()
            self.lock.acquire()
            self.lock.wait()
            self.lock.release()
        pass

    def close(self):
        self.interrupted = True
        pass

    pass


class WorkThreadLock(Condition):
    def __init__(self, max_workers):
        super(WorkThreadLock, self).__init__()
        self.count = 0  # 运行中的线程数量
        self.max_workers = max_workers  # 运行中线程最大数量
        pass

    def increase(self):
        self.acquire()
        self.count += 1
        self.release()
        pass

    def reduce(self):
        self.acquire()
        if self.count > 0:
            self.count -= 1
        if self.count == self.max_workers - 1:
            self.notify()
        self.release()
        pass

    pass
