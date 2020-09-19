import warnings
warnings.filterwarnings('ignore')
import numpy as np
import copy as cp
import operator
from preprocessing import preprocess #Our class
prepro = preprocess()
import extract_features
import pycrfsuite
import math 


def load_model(engine='ws1000'):
    '''
    engine : String type, Segmenter mode; ws1000,tnhc use CRF; tl-deepcut need to load model
    '''
    print('loading model.....')
    if engine != 'deepcut':
        if 'tl-deepcut' in engine:
            try:
                model_load = extract_features.get_convo_nn2()
                engine_type = engine.split('-')[2]
                model_load.load_weights(f'scads_cut/weight/model_weight_{engine_type}.h5')
            except:
                raise Exception('Error Engine TL-XXXX-CORPUS_NAME')  
        else: 
            model_load = pycrfsuite.Tagger() 
            model_load.open(f'model/crf_{engine}_entropyfrom_dc_bl_full_socialDict.model')
        global model; model = model_load
    else:
        pass
    print('Success')
    global engine_mode; engine_mode = engine

def return_max_index(number_ranking,entropy_list):
    '''
    Sentence by Sentence
    number_ranking : top-k percentile value (int 1-100)
    entropy_list : Entropy of each character ex. [0.5,0.1,0.4,0.3,0.1]
    '''
    index_entropy = []
    func_entro_list = entropy_list[:]
    ranking_ = int(len(entropy_list)*(number_ranking/100))
    for _ in range(ranking_):
        index, _ = max(enumerate(func_entro_list), key=operator.itemgetter(1))
        func_entro_list[index] = -math.inf
        index_entropy.append(index)
    return index_entropy

def scoring_function(x_function,y_dg_pred,y_entropy_function,y_prob_function,entropy_index):
    '''
    Sentence by Sentence
    x_function : text input (feature) ex. ['Hello, my name is ping','Hello, world']
    y_dg_pred : answer from DG model (copy and delete)
    y_entropy_function: Entropy of each character ex. [0.5,0.1,0.4,0.3,0.1]
    y_entropy_function: Probability of each character ex. [0.5,0.1,0.4,0.3,0.1]
    entropy_index: Index of highest entropy in top-k ex. [13,7,3,1,9]
    '''
    result = y_dg_pred[:]
    del y_dg_pred

    for i,items in enumerate(entropy_index):
        x_data = extract_features.extract_features_crf(x_function[i],i,y_entropy_function,y_prob_function)
        for idx in items:
            y_pred_crf = model.tag(x_data[idx])
            result[i][idx] = int(y_pred_crf[0])
    return result

def cut(y_pred_boolean,x_data):
    x_ = x_data[:]
    answer = []
    for idx,items in enumerate(y_pred_boolean):
        text = ""
        for index,item in enumerate(items):
            if(item == 1):
                text +='|'
            text +=x_[idx][index]
        answer.append(text)
    return answer 

def predict(sent,k):
    '''

    '''
    if 'tl-deepcut' in engine_mode:
        y_pred=[]
        y_pred = [model.predict(prepro.create_feature_array(item)) for item in sent]
        y_pred_ = prepro.preprocessing_y_pred(y_pred)
        y_pred = list(map(prepro.argmax_function,y_pred_))
        x_answer = cut(y_pred,sent)
    else:
        y_original,y_entropy_original,y_prob_original,_,_,_,_ = prepro.predict_(sent,og='true') # DeepCut Baseline/BEST+WS/WS
        if engine_mode == 'deepcut':
            x_answer = cut(y_original,sent)
        else:
            entropy_index = [return_max_index(k,value) for value in y_entropy_original] # Find entropy index from DC Baseline
            answer_ds_original = scoring_function(sent,y_original,y_entropy_original,y_prob_original,entropy_index) # Score function
            x_answer = cut(answer_ds_original,sent)
    return [x_text.split('|')[1:] for x_text in x_answer]

def tokenize(sent,k=1):
    if type(sent) != list:
        sent = [sent]

    if k == 1:
        if engine_mode == 'lst20':
            k =  30
        elif engine_mode == 'tnhc':
            k =  36
        else: #ws
            k = 100 #27
    ans = map(predict,[sent],np.full(np.array(sent).shape, k))
    return list(ans)[0]