from static.darkflow_video.darkflow.cli import cliHandler


def run(filename):
    cliHandler(
        ['flow', '--model', 'static/darkflow_video/cfg/yolo.cfg', '--load', 'static/darkflow_video/bin/yolo.weights',
         '--demo', filename])



if __name__ == '__main__':
    run('static/video/555.mp4')
