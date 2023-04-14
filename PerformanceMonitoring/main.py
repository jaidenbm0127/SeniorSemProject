from PerformanceMonitoring.processor import Processor


def main():
    proc = Processor()
    # Loop to keep  the collection of processes continuing.

    x = 0
    while x < 200:
        proc.process()
        x += 1

    proc.save()


if __name__ == '__main__':
    main()
