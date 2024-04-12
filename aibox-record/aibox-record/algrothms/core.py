


class AIboxRecordCore:
    model_cls = None

    def __init__(self, model_fp):
        self.mdoel = self.init_model(model_fp)
    
    def init_model(self, model_fp):
        pass

    def predict(self, raw):
        return [{
            'label': 'person',
            'class_id': 0,
            'prob': 0.9,
            'box': {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}
        }]