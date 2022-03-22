import torch
import sys

def validate_state_dicts(model_state_dict_1, model_state_dict_2):
  if len(model_state_dict_1) != len(model_state_dict_2):
    print(f"Length mismatch: {len(model_state_dict_1)}, {len(model_state_dict_2)}")
    return False
  # Replicate modules have "module" attached to their keys, so strip these off when comparing to local model.
  if next(iter(model_state_dict_1.keys())).startswith("module"):
    model_state_dict_1 = {k[len("module") + 1 :]: v for k, v in model_state_dict_1.items()}

  if next(iter(model_state_dict_2.keys())).startswith("module"):
    model_state_dict_2 = {k[len("module") + 1 :]: v for k, v in model_state_dict_2.items()}

  for ((k_1, v_1), (k_2, v_2)) in zip(
    model_state_dict_1.items(), model_state_dict_2.items()):
    if k_1 != k_2:
      print(f"Key mismatch: {k_1} vs {k_2}")
      return False

    # convert both to the same CUDA device
    if str(v_1.device) != "cuda:0":
      v_1 = v_1.to("cuda:0" if torch.cuda.is_available() else "cpu")
    if str(v_2.device) != "cuda:0":
      v_2 = v_2.to("cuda:0" if torch.cuda.is_available() else "cpu")
    if not torch.allclose(v_1, v_2):
      print(f"Tensor mismatch: {v_1} vs {v_2}")
      #return False
    #print(f"Tensors: {v_1} vs {v_2}")
    


def check(model1, model2):
  for p1, p2 in zip(model1.parameters(), model2.parameters()):
    if p1.data.ne(p2.data).sum() > 0:
      return False
  return True

def compare_models(model_1, model_2):
    models_differ = 0
    for key_item_1, key_item_2 in zip(model_1.state_dict().items(), model_2.state_dict().items()):
        if torch.equal(key_item_1[1], key_item_2[1]):
            pass
        else:
            models_differ += 1
            if (key_item_1[0] == key_item_2[0]):
                print('Mismtach found at', key_item_1[0])
            else:
                raise Exception
    if models_differ == 0:
        print('Models match perfectly! :)')

model1 = torch.load("evals/logs/femnist/0316_134349/aggregator/GlobalModel_post_ep30_Agg2")
model2 = torch.load("evals/logs/femnist/0316_134349/aggregator/GlobalModel_post_ep30_Agg3")

validate_state_dicts(model1.state_dict(), model2.state_dict())
compare_models(model1, model2)