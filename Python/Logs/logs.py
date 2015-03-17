class LogParser(object):

    def __init__(self, log_file):
        self.log_file = log_file
        self.index_map = dict()
        self.index_log()

    def reset_log(self):
        self.log_file.seek(0)

    def index_log(self):
        for i, line in enumerate(self.log_file):
            parsed_line = Line(line)
            if parsed_line.tag not in self.index_map:
                self.index_map[parsed_line.tag] = [i]
            else:
                self.index_map[parsed_line.tag].append(i)
        self.reset_log()

    def display_lines_with_tag(self, tag):
        if tag not in self.index_map:
            print tag + ' not found in log file'
        else:
            for ind in self.index_map[tag]:
                print self.get_line_by_ind(ind)

        self.reset_log()

    def get_lines_with_tag(self, tag):
        if tag not in self.index_map:
            print tag + ' not found in log file'
        else:
            return [self.get_line_by_ind(ind) for ind in self.index_map[tag]]

    def get_line_by_ind(self, ind):
        self.log_file.seek(ind)
        return self.log_file.readline()


class Line(object):

    def __init__(self, s):
        self.string = s
        fields = s.split()
        self.date = fields[0]
        self.time = fields[1]
        self.tag = fields[2]
        if len(fields) > 3:
            self.val = fields[3]
        else:
            pass