import argparse

from tensorflow.python.keras.backend import set_session

from metrics import *
from utils_network import *
from model_network import cyclegan
import tensorflow as tf
import networkx as nx
import matplotlib.pyplot as plt
import os
from gae.train import gae
import pickle


def main(_):
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--demo', dest='demo', action='store_true', help='Demo')
    # parser.add_argument('--dataset_A', dest='dataset_A', default='corsegraph_bitcoin.mat', help='path of the data set')
    # parser.add_argument('--dataset_A', dest='dataset_A', default='email-Eu-core.mat', help='path of the data set')
    # parser.add_argument('--dataset_A', dest='dataset_A', default='old_cora.mat', help='p`ath of the data set')
    parser.add_argument('--dataset_A', dest='dataset_A', default='cora.mat', help='path of the data set')
    # parser.add_argument('--parse_data_lang', dest='parse_data_lang', default='python', help='In what language did the parse_data program run?')
    # parser.add_argument('--dataset_A', dest='dataset_A', default='matlab-email.mat', help='path of the data set')
    # parser.add_argument('--checkpoint', dest='checkpoint', default='./checkpoint_email', help='path of the checkpoint')
    parser.add_argument('--checkpoint', dest='checkpoint', default='./checkpoint_training_cora',
                        help='path of the checkpoint')
    # parser.add_argument('--filename', dest='filename', default='output_network', help='the filename of output network')
    parser.add_argument('--filename', dest='filename', default='cora_output_network',
                        help='the filename of output network')
    parser.add_argument('--epoch', dest='epoch', type=int, default=250, help='# of epoch')
    parser.add_argument('--layer', dest='layer', type=int, default=5, help='# of layer')
    parser.add_argument('--clusters', dest='clusters', type=int, default=2, help='# of clusters, 2 or 3')
    # parser.add_argument('--output_dir', dest='output_dir', default='./output_dir_email', help='results are saved here')
    # parser.add_argument('--output_dir', dest='output_dir', default='./output_dir_cora', help='results are saved here')
    parser.add_argument('--output_dir', dest='output_dir', default='./output_dir_cora', help='results are saved here')
    parser.add_argument('--use_resnet', dest='use_resnet', type=str, default=True,
                        help='generation network using reidule block')
    parser.add_argument('--use_lsgan', dest='use_lsgan', default=True, help='gan loss defined in lsgan')
    parser.add_argument('--which_direction', dest='which_direction', default='BtoA', help='AtoB or BtoA')
    parser.add_argument('--stage', dest='which_stage', default='testing', help='training stage or testing stage')
    parser.add_argument('--starting_layer', dest='starting_layer', type=int, default=1, help='the starting layer')
    parser.add_argument('--shuffle', dest='shuffle', action='store_true', help='Shuffle the graph')
    parser.add_argument('--gpu', dest='gpu', action='store_true', help='Use gpu to train the model or not')
    parser.add_argument('--kernel_number', dest='kernel_number', type=int, default=32, help='Shuffle the graph')
    parser.add_argument('--iter', dest='iter', type=int, default=5,
                        help='Iterations of residule_block function for generator to train graph')
    args = parser.parse_args()
    # dataset = ['coarsegraph_facebook.mat','coarsegraph_p2p.mat','email-Eu-core.mat','coarsegraph_wiki.mat']

    if args.demo:
        args.dataset_A = 'email-Eu-core.mat'
        args.layer = 5
        args.starting_layer = 0
        args.kernel_number = 32
        args.iter = 7
        args.checkpoint = './checkpoint_email'
        args.output_dir = './output_dir_email'
    # --- initialization --- #
    tfconfig = tf.ConfigProto(allow_soft_placement=True)
    tfconfig.gpu_options.allow_growth = True
    # use this to disable the gpu usage of tensorflow
    #tfconfig.gpu_options.allow_growth = False
    #os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    if args.gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    if args.which_stage == 'training':
        if not os.path.isfile('./data/{}'.format(args.dataset_A)):
            print('Start calling AMG algorithm to create data set!')
            os.system("matlab -nodisplay -nosplash -nodesktop -r Parsedata")
            print('Finish generating graph data set!')

        data_A, data_B, indices, P, A, edges, R = preproc_data(tf.Session(config=tfconfig), args)
        # --- training process --- #
        for layer_idx in range(args.starting_layer, args.layer):
            model = cyclegan(args, data_A['l{}_1'.format(layer_idx + 1)], data_B['l{}_1'.format(layer_idx + 1)])
            model.train(layer_idx)
    elif args.which_stage == 'testing':
        data_A, data_B, indices, P, A, edges, R = preproc_data(tf.Session(config=tfconfig), args)
        # --- generating synthetic network --- #
        generate_network(data_A, data_B, indices, P, A, args)
        # --- evaluation --- #
        save_graph(args, R, edges)
        print('Original graph and synthetic graph generated by Music-GAN have been saved at directory: {}.'.format(
            args.output_dir))
        gae(args.dataset_A, args.output_dir)
        print('Evaluation Results:')
        evaluation(args)
        # netgan = np.load('{}/netgan_network.npy'.format(args.output_dir))
        # a = compute_graph_statistics(netgan[1])
        # print(a)
        # with open('./{}/netgan_network_statistics.pickle'.format(args.checkpoint), 'wb') as handle:
        #     pickle.dump(a, handle, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        print('stage should be either training or testing.')

    # data_A, data_B, indices, P, A, edges = preproc_data(tf.Session(config=tfconfig), args)
    # --- generating synthetic network --- #
    # generate_network(data_A, data_B, indices, P, A, args)
    # # --- evaluation --- #
    # # save_graph(args, edges)
    # print('Original graph and synthetic graph generated by Music-GAN have been saved at directory: {}.'.format(
    #     args.output_dir))
    # gae(args.dataset_A, args.output_dir)
    # print('Evaluation Results:')
    # evaluation(args)


# --- testing stage --- #
def generate_network(data_A, data_B, indices, P, A, args):
    #  --- for testing --- #
    filename = args.filename
    image_path = os.path.join(args.output_dir, args.which_direction)
    network_A = [[] for _ in range(args.starting_layer, args.layer)]
    network_coarse = [[] for _ in range(args.starting_layer, args.layer)]
    if not os.path.exists(image_path):
        os.makedirs(image_path)
    for l in range(args.layer - args.starting_layer):
        model = cyclegan(args, data_A, data_B)
        network_A[l], network_coarse[l] = model.test(args.which_direction, indices, data_B, P, l + args.starting_layer)
        tf.reset_default_graph()
    A = np.array(A)
    np.save('{}/{}.npy'.format(args.output_dir, filename), network_coarse)
    np.save('{}/org_network.npy'.format(args.output_dir), A[args.starting_layer:args.layer])
    network_B = np.array(np.sum(network_A, axis=0) / (args.layer - args.starting_layer))
    length = len(network_B)
    network_B = network_B[1:length, :][:, 1:length]
    A = A[0][1:length, :][:, 1:length]
    A = A + A.T
    A[A > 1] = 1
    DD = np.sort(network_B.flatten())[::-1]
    threshold = DD[int(np.sum(A))]
    network_C = np.array([[0 if network_B[i, j] < threshold else 1 for i in range(network_B.shape[0])] for j in
                          range(network_B.shape[1])], dtype=np.int8)

    # org_network = np.array([[0 if A[i, j] < threshold else 1 for i in range(A.shape[0])] for j
    #                         in range(A.shape[1])])
    np.save('{}/{}.npy'.format(args.output_dir, filename), network_C)
    np.save('{}/org_network.npy'.format(args.output_dir), A)

    print('Computing metrics for original graph')
    b = compute_graph_statistics(A)
    with open('./{}/org_network_statistics.pickle'.format(args.checkpoint), 'wb') as handle:
        pickle.dump(b, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(b)
    print('Computing metrics for graph generated by Music-GAN')
    a = compute_graph_statistics(network_C)
    print(a)
    with open('./{}/music_network_statistics.pickle'.format(args.checkpoint), 'wb') as handle:
        pickle.dump(a, handle, protocol=pickle.HIGHEST_PROTOCOL)
    evaluation2(args, A)


def evaluation(args):
    degree(args.output_dir)
    coefficient(args.output_dir)


def evaluation2(args, original_network):
    n = original_network.shape[0]
    m = int(np.sum(original_network))
    random_ER_G = nx.gnm_random_graph(n, m)
    random_bara_G = nx.generators.random_graphs.barabasi_albert_graph(n, 250)
    ER_G = nx.to_numpy_matrix(random_ER_G)
    bara_G = nx.to_numpy_matrix(random_bara_G)
    np.save('{}/ER.npy'.format(args.output_dir), ER_G)
    np.save('{}/BA.npy'.format(args.output_dir), bara_G)
    # ER_G = ER_G  + ER_G .T
    # ER_G[ER_G  > 1] = 1
    # bara_G = bara_G  + bara_G .T
    # bara_G[bara_G  > 1] = 1
    ER_G = np.array(ER_G)
    bara_G = np.array(bara_G)
    print('Computing metrics for ER graph')
    c = compute_graph_statistics(ER_G)
    with open('./{}/ER_statistics.pickle'.format(args.checkpoint), 'wb') as handle:
        pickle.dump(c, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(c)
    print('Computing metrics for bara graph')
    d = compute_graph_statistics(bara_G)
    with open('./{}/bara_statistics.pickle'.format(args.checkpoint), 'wb') as handle:
        pickle.dump(d, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(d)


def save_graph(args, R, edges):
    filename = args.filename
    A = np.load('{}/org_network.npy'.format(args.output_dir))
    network_B = np.load('{}/{}.npy'.format(args.output_dir, filename))
    # netgan = np.load('{}/netgan_network.npy'.format(args.output_dir))[1]
    tfconfig = tf.ConfigProto(allow_soft_placement=True)
    tfconfig.gpu_options.allow_growth = True
    sess = tf.Session(config=tfconfig)
    n = R[0, 0].shape[1]
    # if netgan.shape[0] < n:
    #     # Net = np.zeros((n, n))
    #     R[0, 0] = R[0, 0][:netgan.shape[0], :netgan.shape[1]]
    # netgan_copy = netgan
    # netgan_disp = [netgan]
    # for i in range(1, args.layer):
    #     adjacent_matrix = tf.placeholder(tf.float32, shape=netgan_copy.shape)
    #     R_matrix = tf.placeholder(tf.float32, shape=R[i - 1, 0].shape)
    #     netgan_copy = sess.run(tf.matmul(tf.matmul(R_matrix, adjacent_matrix), tf.transpose(R_matrix)),
    #                       feed_dict={R_matrix: R[i - 1, 0].todense(), adjacent_matrix: netgan_copy})
    #     DD = np.sort(netgan_copy.flatten())[::-1]
    #     threshold = DD[edges[0, i]]
    #     network_C = np.array([[0 if netgan_copy[i, j] < threshold else 1 for i in range(netgan_copy.shape[0])] for j in
    #                           range(netgan_copy.shape[1])], dtype=np.int8)
    #     netgan_disp.append(network_C)
    for l in range(5):
        # netgan_G = nx.from_numpy_matrix(netgan_disp[l])
        # netgan_pos = nx.spring_layout(netgan_G)

        G = nx.from_numpy_matrix(A)
        pos = nx.spring_layout(G)
        gen_G = nx.from_numpy_matrix(network_B)
        gen_pos = nx.spring_layout(gen_G)
        nx.draw_networkx_nodes(gen_G, gen_pos, node_size=10, edge_vmin=0.0, edge_vmax=0.1, node_color='blue',
                               alpha=0.8)
        # nx.draw_networkx_edges(gen_G, gen_pos,  alpha=0.7)
        plt.savefig('./{}/generated_graph_l_{}_without_edge'.format(args.output_dir, l + args.starting_layer), dpi=1000)
        plt.close()

        nx.draw_networkx_nodes(G, pos, node_size=10, edge_vmin=0.0, edge_vmax=0.1, node_color='blue', alpha=0.8)
        # nx.draw_networkx_edges(G, pos, alpha=0.7)
        plt.savefig('./{}/original_graph_l_{}_without_edge'.format(args.output_dir, l + args.starting_layer), dpi=1000)
        plt.close()

        nx.draw_networkx_nodes(gen_G, gen_pos, node_size=10, edge_vmin=0.0, edge_vmax=0.1, node_color='blue',
                               alpha=0.8)
        nx.draw_networkx_edges(gen_G, gen_pos, alpha=0.1)
        plt.savefig('./{}/generated_graph_l_{}_with_edge'.format(args.output_dir, l + args.starting_layer), dpi=1000)
        plt.close()

        nx.draw_networkx_nodes(G, pos, node_size=10, edge_vmin=0.0, edge_vmax=0.1, node_color='blue', alpha=0.8)
        nx.draw_networkx_edges(G, pos, alpha=0.1)
        plt.savefig('./{}/original_graph_l_{}_with_edge'.format(args.output_dir, l + args.starting_layer), dpi=1000)
        plt.close()

        # nx.draw_networkx_nodes(netgan_G, netgan_pos, node_size=10, edge_vmin=0.0, edge_vmax=0.1, node_color='blue',
        #                        alpha=0.8)
        # plt.savefig('./{}/netgan_graph_l_{}_without_edge'.format(args.output_dir, l + args.starting_layer), dpi=1000)
        # plt.close()
        # nx.draw_networkx_nodes(netgan_G, netgan_pos, node_size=10, edge_vmin=0.0, edge_vmax=0.1, node_color='blue', alpha=0.8)
        # nx.draw_networkx_edges(netgan_G, netgan_pos, alpha=0.1)
        # plt.savefig('./{}/netgan_graph_l_{}_with_edge'.format(args.output_dir, l + args.starting_layer), dpi=1000)
        # plt.close()


if __name__ == '__main__':
    tf.app.run()
