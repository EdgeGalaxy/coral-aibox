import time

from schema import FeatureDBParamsModel
from algrothms.featuredb import FeatureDB

feature_params = FeatureDBParamsModel(weight_name="resnet18-f37072fd")


f = FeatureDB(
    width=224,
    height=224,
    weight_path=feature_params.weight_path,
    model_type=feature_params.model_type,
    device_id=feature_params.device_id,
    db_path=feature_params.db_path,
    db_size=feature_params.db_size,
    sim_threshold=feature_params.sim_threshold,
)


for i in range(10):
    t = time.time()
    idx = i % len(f.fake_persons_features)
    feature = f.fake_persons_features[idx]
    f.compare(feature)
    et = time.time()
    print(f"{i} cost {et - t} s")
