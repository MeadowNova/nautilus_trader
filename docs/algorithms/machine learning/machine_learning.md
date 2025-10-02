"""
Implementation of gradient descent algorithm for minimizing cost of a linear hypothesis
function.
"""

import numpy as np

# List of input, output pairs
train_data = (
    ((5, 2, 3), 15),
    ((6, 5, 9), 25),
    ((11, 12, 13), 41),
    ((1, 1, 1), 8),
    ((11, 12, 13), 41),
)
test_data = (((515, 22, 13), 555), ((61, 35, 49), 150))
parameter_vector = [2, 4, 1, 5]
m = len(train_data)
LEARNING_RATE = 0.009


def _error(example_no, data_set="train"):
    """
    :param data_set: train data or test data
    :param example_no: example number whose error has to be checked
    :return: error in example pointed by example number.
    """
    return calculate_hypothesis_value(example_no, data_set) - output(
        example_no, data_set
    )


def _hypothesis_value(data_input_tuple):
    """
    Calculates hypothesis function value for a given input
    :param data_input_tuple: Input tuple of a particular example
    :return: Value of hypothesis function at that point.
    Note that there is an 'biased input' whose value is fixed as 1.
    It is not explicitly mentioned in input data.. But, ML hypothesis functions use it.
    So, we have to take care of it separately. Line 36 takes care of it.
    """
    hyp_val = 0
    for i in range(len(parameter_vector) - 1):
        hyp_val += data_input_tuple[i] * parameter_vector[i + 1]
    hyp_val += parameter_vector[0]
    return hyp_val


def output(example_no, data_set):
    """
    :param data_set: test data or train data
    :param example_no: example whose output is to be fetched
    :return: output for that example
    """
    if data_set == "train":
        return train_data[example_no][1]
    elif data_set == "test":
        return test_data[example_no][1]
    return None


def calculate_hypothesis_value(example_no, data_set):
    """
    Calculates hypothesis value for a given example
    :param data_set: test data or train_data
    :param example_no: example whose hypothesis value is to be calculated
    :return: hypothesis value for that example
    """
    if data_set == "train":
        return _hypothesis_value(train_data[example_no][0])
    elif data_set == "test":
        return _hypothesis_value(test_data[example_no][0])
    return None


def summation_of_cost_derivative(index, end=m):
    """
    Calculates the sum of cost function derivative
    :param index: index wrt derivative is being calculated
    :param end: value where summation ends, default is m, number of examples
    :return: Returns the summation of cost derivative
    Note: If index is -1, this means we are calculating summation wrt to biased
        parameter.
    """
    summation_value = 0
    for i in range(end):
        if index == -1:
            summation_value += _error(i)
        else:
            summation_value += _error(i) * train_data[i][0][index]
    return summation_value


def get_cost_derivative(index):
    """
    :param index: index of the parameter vector wrt to derivative is to be calculated
    :return: derivative wrt to that index
    Note: If index is -1, this means we are calculating summation wrt to biased
        parameter.
    """
    cost_derivative_value = summation_of_cost_derivative(index, m) / m
    return cost_derivative_value


def run_gradient_descent():
    global parameter_vector
    # Tune these values to set a tolerance value for predicted output
    absolute_error_limit = 0.000002
    relative_error_limit = 0
    j = 0
    while True:
        j += 1
        temp_parameter_vector = [0, 0, 0, 0]
        for i in range(len(parameter_vector)):
            cost_derivative = get_cost_derivative(i - 1)
            temp_parameter_vector[i] = (
                parameter_vector[i] - LEARNING_RATE * cost_derivative
            )
        if np.allclose(
            parameter_vector,
            temp_parameter_vector,
            atol=absolute_error_limit,
            rtol=relative_error_limit,
        ):
            break
        parameter_vector = temp_parameter_vector
    print(("Number of iterations:", j))


def test_gradient_descent():
    for i in range(len(test_data)):
        print(("Actual output value:", output(i, "test")))
        print(("Hypothesis output:", calculate_hypothesis_value(i, "test")))


if __name__ == "__main__":
    run_gradient_descent()
    print("\nTesting gradient descent for a linear hypothesis function.\n")
    test_gradient_descent()



—----------------------------------------------------------------------------------------

"""
Linear regression is the most basic type of regression commonly used for
predictive analysis. The idea is pretty simple: we have a dataset and we have
features associated with it. Features should be chosen very cautiously
as they determine how much our model will be able to make future predictions.
We try to set the weight of these features, over many iterations, so that they best
fit our dataset. In this particular code, I had used a CSGO dataset (ADR vs
Rating). We try to best fit a line through dataset and estimate the parameters.
"""

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
#     "numpy",
# ]
# ///

import httpx
import numpy as np


def collect_dataset():
    """Collect dataset of CSGO
    The dataset contains ADR vs Rating of a Player
    :return : dataset obtained from the link, as matrix
    """
    response = httpx.get(
        "https://raw.githubusercontent.com/yashLadha/The_Math_of_Intelligence/"
        "master/Week1/ADRvsRating.csv",
        timeout=10,
    )
    lines = response.text.splitlines()
    data = []
    for item in lines:
        item = item.split(",")
        data.append(item)
    data.pop(0)  # This is for removing the labels from the list
    dataset = np.matrix(data)
    return dataset


def run_steep_gradient_descent(data_x, data_y, len_data, alpha, theta):
    """Run steep gradient descent and updates the Feature vector accordingly_
    :param data_x   : contains the dataset
    :param data_y   : contains the output associated with each data-entry
    :param len_data : length of the data_
    :param alpha    : Learning rate of the model
    :param theta    : Feature vector (weight's for our model)
    ;param return    : Updated Feature's, using
                       curr_features - alpha_ * gradient(w.r.t. feature)
    >>> import numpy as np
    >>> data_x = np.array([[1, 2], [3, 4]])
    >>> data_y = np.array([5, 6])
    >>> len_data = len(data_x)
    >>> alpha = 0.01
    >>> theta = np.array([0.1, 0.2])
    >>> run_steep_gradient_descent(data_x, data_y, len_data, alpha, theta)
    array([0.196, 0.343])
    """
    n = len_data

    prod = np.dot(theta, data_x.transpose())
    prod -= data_y.transpose()
    sum_grad = np.dot(prod, data_x)
    theta = theta - (alpha / n) * sum_grad
    return theta


def sum_of_square_error(data_x, data_y, len_data, theta):
    """Return sum of square error for error calculation
    :param data_x    : contains our dataset
    :param data_y    : contains the output (result vector)
    :param len_data  : len of the dataset
    :param theta     : contains the feature vector
    :return          : sum of square error computed from given feature's

    Example:
    >>> vc_x = np.array([[1.1], [2.1], [3.1]])
    >>> vc_y = np.array([1.2, 2.2, 3.2])
    >>> round(sum_of_square_error(vc_x, vc_y, 3, np.array([1])),3)
    np.float64(0.005)
    """
    prod = np.dot(theta, data_x.transpose())
    prod -= data_y.transpose()
    sum_elem = np.sum(np.square(prod))
    error = sum_elem / (2 * len_data)
    return error


def run_linear_regression(data_x, data_y):
    """Implement Linear regression over the dataset
    :param data_x  : contains our dataset
    :param data_y  : contains the output (result vector)
    :return        : feature for line of best fit (Feature vector)
    """
    iterations = 100000
    alpha = 0.0001550

    no_features = data_x.shape[1]
    len_data = data_x.shape[0] - 1

    theta = np.zeros((1, no_features))

    for i in range(iterations):
        theta = run_steep_gradient_descent(data_x, data_y, len_data, alpha, theta)
        error = sum_of_square_error(data_x, data_y, len_data, theta)
        print(f"At Iteration {i + 1} - Error is {error:.5f}")

    return theta


def mean_absolute_error(predicted_y, original_y):
    """Return sum of square error for error calculation
    :param predicted_y   : contains the output of prediction (result vector)
    :param original_y    : contains values of expected outcome
    :return          : mean absolute error computed from given feature's

    >>> predicted_y = [3, -0.5, 2, 7]
    >>> original_y = [2.5, 0.0, 2, 8]
    >>> mean_absolute_error(predicted_y, original_y)
    0.5
    """
    total = sum(abs(y - predicted_y[i]) for i, y in enumerate(original_y))
    return total / len(original_y)


def main():
    """Driver function"""
    data = collect_dataset()

    len_data = data.shape[0]
    data_x = np.c_[np.ones(len_data), data[:, :-1]].astype(float)
    data_y = data[:, -1].astype(float)

    theta = run_linear_regression(data_x, data_y)
    len_result = theta.shape[1]
    print("Resultant Feature vector : ")
    for i in range(len_result):
        print(f"{theta[0, i]:.5f}")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    main()

—-------------------------------------------------------------------------------

#!/usr/bin/python

# Logistic Regression from scratch

# In[62]:

# In[63]:

# importing all the required libraries

"""
Implementing logistic regression for classification problem
Helpful resources:
Coursera ML course
https://medium.com/@martinpella/logistic-regression-from-scratch-in-python-124c5636b8ac
"""

import numpy as np
from matplotlib import pyplot as plt
from sklearn import datasets

# get_ipython().run_line_magic('matplotlib', 'inline')


# In[67]:

# sigmoid function or logistic function is used as a hypothesis function in
# classification problems


def sigmoid_function(z: float | np.ndarray) -> float | np.ndarray:
    """
    Also known as Logistic Function.

                1
    f(x) =   -------
              1 + e⁻ˣ

    The sigmoid function approaches a value of 1 as its input 'x' becomes
    increasing positive. Opposite for negative values.

    Reference: https://en.wikipedia.org/wiki/Sigmoid_function

    @param z:  input to the function
    @returns: returns value in the range 0 to 1

    Examples:
    >>> float(sigmoid_function(4))
    0.9820137900379085
    >>> sigmoid_function(np.array([-3, 3]))
    array([0.04742587, 0.95257413])
    >>> sigmoid_function(np.array([-3, 3, 1]))
    array([0.04742587, 0.95257413, 0.73105858])
    >>> sigmoid_function(np.array([-0.01, -2, -1.9]))
    array([0.49750002, 0.11920292, 0.13010847])
    >>> sigmoid_function(np.array([-1.3, 5.3, 12]))
    array([0.21416502, 0.9950332 , 0.99999386])
    >>> sigmoid_function(np.array([0.01, 0.02, 4.1]))
    array([0.50249998, 0.50499983, 0.9836975 ])
    >>> sigmoid_function(np.array([0.8]))
    array([0.68997448])
    """
    return 1 / (1 + np.exp(-z))


def cost_function(h: np.ndarray, y: np.ndarray) -> float:
    """
    Cost function quantifies the error between predicted and expected values.
    The cost function used in Logistic Regression is called Log Loss
    or Cross Entropy Function.

    J(θ) = (1/m) * Σ [ -y * log(hθ(x)) - (1 - y) * log(1 - hθ(x)) ]

    Where:
       - J(θ) is the cost that we want to minimize during training
       - m is the number of training examples
       - Σ represents the summation over all training examples
       - y is the actual binary label (0 or 1) for a given example
       - hθ(x) is the predicted probability that x belongs to the positive class

    @param h: the output of sigmoid function. It is the estimated probability
    that the input example 'x' belongs to the positive class

    @param y: the actual binary label associated with input example 'x'

    Examples:
    >>> estimations = sigmoid_function(np.array([0.3, -4.3, 8.1]))
    >>> cost_function(h=estimations,y=np.array([1, 0, 1]))
    0.18937868932131605
    >>> estimations = sigmoid_function(np.array([4, 3, 1]))
    >>> cost_function(h=estimations,y=np.array([1, 0, 0]))
    1.459999655669926
    >>> estimations = sigmoid_function(np.array([4, -3, -1]))
    >>> cost_function(h=estimations,y=np.array([1,0,0]))
    0.1266663223365915
    >>> estimations = sigmoid_function(0)
    >>> cost_function(h=estimations,y=np.array([1]))
    0.6931471805599453

    References:
       - https://en.wikipedia.org/wiki/Logistic_regression
    """
    return float((-y * np.log(h) - (1 - y) * np.log(1 - h)).mean())


def log_likelihood(x, y, weights):
    scores = np.dot(x, weights)
    return np.sum(y * scores - np.log(1 + np.exp(scores)))


# here alpha is the learning rate, X is the feature matrix,y is the target matrix
def logistic_reg(alpha, x, y, max_iterations=70000):
    theta = np.zeros(x.shape[1])

    for iterations in range(max_iterations):
        z = np.dot(x, theta)
        h = sigmoid_function(z)
        gradient = np.dot(x.T, h - y) / y.size
        theta = theta - alpha * gradient  # updating the weights
        z = np.dot(x, theta)
        h = sigmoid_function(z)
        j = cost_function(h, y)
        if iterations % 100 == 0:
            print(f"loss: {j} \t")  # printing the loss after every 100 iterations
    return theta


# In[68]:

if __name__ == "__main__":
    import doctest

    doctest.testmod()

    iris = datasets.load_iris()
    x = iris.data[:, :2]
    y = (iris.target != 0) * 1

    alpha = 0.1
    theta = logistic_reg(alpha, x, y, max_iterations=70000)
    print("theta: ", theta)  # printing the theta i.e our weights vector

    def predict_prob(x):
        return sigmoid_function(
            np.dot(x, theta)
        )  # predicting the value of probability from the logistic regression algorithm

    plt.figure(figsize=(10, 6))
    plt.scatter(x[y == 0][:, 0], x[y == 0][:, 1], color="b", label="0")
    plt.scatter(x[y == 1][:, 0], x[y == 1][:, 1], color="r", label="1")
    (x1_min, x1_max) = (x[:, 0].min(), x[:, 0].max())
    (x2_min, x2_max) = (x[:, 1].min(), x[:, 1].max())
    (xx1, xx2) = np.meshgrid(np.linspace(x1_min, x1_max), np.linspace(x2_min, x2_max))
    grid = np.c_[xx1.ravel(), xx2.ravel()]
    probs = predict_prob(grid).reshape(xx1.shape)
    plt.contour(xx1, xx2, probs, [0.5], linewidths=1, colors="black")

    plt.legend()
    plt.show()

=============================================

"""README, Author - Anurag Kumar(mailto:anuragkumarak95@gmail.com)
Requirements:
  - sklearn
  - numpy
  - matplotlib
Python:
  - 3.5
Inputs:
  - X , a 2D numpy array of features.
  - k , number of clusters to create.
  - initial_centroids , initial centroid values generated by utility function(mentioned
    in usage).
  - maxiter , maximum number of iterations to process.
  - heterogeneity , empty list that will be filled with heterogeneity values if passed
    to kmeans func.
Usage:
  1. define 'k' value, 'X' features array and 'heterogeneity' empty list
  2. create initial_centroids,
        initial_centroids = get_initial_centroids(
            X,
            k,
            seed=0 # seed value for initial centroid generation,
                   # None for randomness(default=None)
            )
  3. find centroids and clusters using kmeans function.
        centroids, cluster_assignment = kmeans(
            X,
            k,
            initial_centroids,
            maxiter=400,
            record_heterogeneity=heterogeneity,
            verbose=True # whether to print logs in console or not.(default=False)
            )
  4. Plot the loss function and heterogeneity values for every iteration saved in
     heterogeneity list.
        plot_heterogeneity(
            heterogeneity,
            k
        )
  5. Plot the labeled 3D data points with centroids.
        plot_kmeans(
            X,
            centroids,
            cluster_assignment
        )
  6. Transfers Dataframe into excel format it must have feature called
      'Clust' with k means clustering numbers in it.
"""

import warnings

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.metrics import pairwise_distances

warnings.filterwarnings("ignore")

TAG = "K-MEANS-CLUST/ "


def get_initial_centroids(data, k, seed=None):
    """Randomly choose k data points as initial centroids"""
    # useful for obtaining consistent results
    rng = np.random.default_rng(seed)
    n = data.shape[0]  # number of data points

    # Pick K indices from range [0, N).
    rand_indices = rng.integers(0, n, k)

    # Keep centroids as dense format, as many entries will be nonzero due to averaging.
    # As long as at least one document in a cluster contains a word,
    # it will carry a nonzero weight in the TF-IDF vector of the centroid.
    centroids = data[rand_indices, :]

    return centroids


def centroid_pairwise_dist(x, centroids):
    return pairwise_distances(x, centroids, metric="euclidean")


def assign_clusters(data, centroids):
    # Compute distances between each data point and the set of centroids:
    # Fill in the blank (RHS only)
    distances_from_centroids = centroid_pairwise_dist(data, centroids)

    # Compute cluster assignments for each data point:
    # Fill in the blank (RHS only)
    cluster_assignment = np.argmin(distances_from_centroids, axis=1)

    return cluster_assignment


def revise_centroids(data, k, cluster_assignment):
    new_centroids = []
    for i in range(k):
        # Select all data points that belong to cluster i. Fill in the blank (RHS only)
        member_data_points = data[cluster_assignment == i]
        # Compute the mean of the data points. Fill in the blank (RHS only)
        centroid = member_data_points.mean(axis=0)
        new_centroids.append(centroid)
    new_centroids = np.array(new_centroids)

    return new_centroids


def compute_heterogeneity(data, k, centroids, cluster_assignment):
    heterogeneity = 0.0
    for i in range(k):
        # Select all data points that belong to cluster i. Fill in the blank (RHS only)
        member_data_points = data[cluster_assignment == i, :]

        if member_data_points.shape[0] > 0:  # check if i-th cluster is non-empty
            # Compute distances from centroid to data points (RHS only)
            distances = pairwise_distances(
                member_data_points, [centroids[i]], metric="euclidean"
            )
            squared_distances = distances**2
            heterogeneity += np.sum(squared_distances)

    return heterogeneity


def plot_heterogeneity(heterogeneity, k):
    plt.figure(figsize=(7, 4))
    plt.plot(heterogeneity, linewidth=4)
    plt.xlabel("# Iterations")
    plt.ylabel("Heterogeneity")
    plt.title(f"Heterogeneity of clustering over time, K={k:d}")
    plt.rcParams.update({"font.size": 16})
    plt.show()


def plot_kmeans(data, centroids, cluster_assignment):
    ax = plt.axes(projection="3d")
    ax.scatter(data[:, 0], data[:, 1], data[:, 2], c=cluster_assignment, cmap="viridis")
    ax.scatter(
        centroids[:, 0], centroids[:, 1], centroids[:, 2], c="red", s=100, marker="x"
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("3D K-Means Clustering Visualization")
    plt.show()


def kmeans(
    data, k, initial_centroids, maxiter=500, record_heterogeneity=None, verbose=False
):
    """Runs k-means on given data and initial set of centroids.
    maxiter: maximum number of iterations to run.(default=500)
    record_heterogeneity: (optional) a list, to store the history of heterogeneity
                          as function of iterations
                          if None, do not store the history.
    verbose: if True, print how many data points changed their cluster labels in
                          each iteration"""
    centroids = initial_centroids[:]
    prev_cluster_assignment = None

    for itr in range(maxiter):
        if verbose:
            print(itr, end="")

        # 1. Make cluster assignments using nearest centroids
        cluster_assignment = assign_clusters(data, centroids)

        # 2. Compute a new centroid for each of the k clusters, averaging all data
        #    points assigned to that cluster.
        centroids = revise_centroids(data, k, cluster_assignment)

        # Check for convergence: if none of the assignments changed, stop
        if (
            prev_cluster_assignment is not None
            and (prev_cluster_assignment == cluster_assignment).all()
        ):
            break

        # Print number of new assignments
        if prev_cluster_assignment is not None:
            num_changed = np.sum(prev_cluster_assignment != cluster_assignment)
            if verbose:
                print(
                    f"    {num_changed:5d} elements changed their cluster assignment."
                )

        # Record heterogeneity convergence metric
        if record_heterogeneity is not None:
            # YOUR CODE HERE
            score = compute_heterogeneity(data, k, centroids, cluster_assignment)
            record_heterogeneity.append(score)

        prev_cluster_assignment = cluster_assignment[:]

    return centroids, cluster_assignment


# Mock test below
if False:  # change to true to run this test case.
    from sklearn import datasets as ds

    dataset = ds.load_iris()
    k = 3
    heterogeneity = []
    initial_centroids = get_initial_centroids(dataset["data"], k, seed=0)
    centroids, cluster_assignment = kmeans(
        dataset["data"],
        k,
        initial_centroids,
        maxiter=400,
        record_heterogeneity=heterogeneity,
        verbose=True,
    )
    plot_heterogeneity(heterogeneity, k)
    plot_kmeans(dataset["data"], centroids, cluster_assignment)


def report_generator(
    predicted: pd.DataFrame, clustering_variables: np.ndarray, fill_missing_report=None
) -> pd.DataFrame:
    """
    Generate a clustering report given these two arguments:
        predicted - dataframe with predicted cluster column
        fill_missing_report - dictionary of rules on how we are going to fill in missing
        values for final generated report (not included in modelling);
    >>> predicted = pd.DataFrame()
    >>> predicted['numbers'] = [1, 2, 3]
    >>> predicted['col1'] = [0.5, 2.5, 4.5]
    >>> predicted['col2'] = [100, 200, 300]
    >>> predicted['col3'] = [10, 20, 30]
    >>> predicted['Cluster'] = [1, 1, 2]
    >>> report_generator(predicted, ['col1', 'col2'], 0)
               Features               Type   Mark           1           2
    0    # of Customers        ClusterSize  False    2.000000    1.000000
    1    % of Customers  ClusterProportion  False    0.666667    0.333333
    2              col1    mean_with_zeros   True    1.500000    4.500000
    3              col2    mean_with_zeros   True  150.000000  300.000000
    4           numbers    mean_with_zeros  False    1.500000    3.000000
    ..              ...                ...    ...         ...         ...
    99            dummy                 5%  False    1.000000    1.000000
    100           dummy                95%  False    1.000000    1.000000
    101           dummy              stdev  False    0.000000         NaN
    102           dummy               mode  False    1.000000    1.000000
    103           dummy             median  False    1.000000    1.000000
    <BLANKLINE>
    [104 rows x 5 columns]
    """
    # Fill missing values with given rules
    if fill_missing_report:
        predicted = predicted.fillna(value=fill_missing_report)
    predicted["dummy"] = 1
    numeric_cols = predicted.select_dtypes(np.number).columns
    report = (
        predicted.groupby(["Cluster"])[  # construct report dataframe
            numeric_cols
        ]  # group by cluster number
        .agg(
            [
                ("sum", "sum"),
                ("mean_with_zeros", lambda x: np.mean(np.nan_to_num(x))),
                ("mean_without_zeros", lambda x: x.replace(0, np.nan).mean()),
                (
                    "mean_25-75",
                    lambda x: np.mean(
                        np.nan_to_num(
                            sorted(x)[
                                round(len(x) * 25 / 100) : round(len(x) * 75 / 100)
                            ]
                        )
                    ),
                ),
                ("mean_with_na", "mean"),
                ("min", lambda x: x.min()),
                ("5%", lambda x: x.quantile(0.05)),
                ("25%", lambda x: x.quantile(0.25)),
                ("50%", lambda x: x.quantile(0.50)),
                ("75%", lambda x: x.quantile(0.75)),
                ("95%", lambda x: x.quantile(0.95)),
                ("max", lambda x: x.max()),
                ("count", lambda x: x.count()),
                ("stdev", lambda x: x.std()),
                ("mode", lambda x: x.mode()[0]),
                ("median", lambda x: x.median()),
                ("# > 0", lambda x: (x > 0).sum()),
            ]
        )
        .T.reset_index()
        .rename(index=str, columns={"level_0": "Features", "level_1": "Type"})
    )  # rename columns
    # calculate the size of cluster(count of clientID's)
    # avoid SettingWithCopyWarning
    clustersize = report[
        (report["Features"] == "dummy") & (report["Type"] == "count")
    ].copy()
    # rename created predicted cluster to match report column names
    clustersize.Type = "ClusterSize"
    clustersize.Features = "# of Customers"
    # calculating the proportion of cluster
    clusterproportion = pd.DataFrame(
        clustersize.iloc[:, 2:].to_numpy() / clustersize.iloc[:, 2:].to_numpy().sum()
    )
    # rename created predicted cluster to match report column names
    clusterproportion["Type"] = "% of Customers"
    clusterproportion["Features"] = "ClusterProportion"
    cols = clusterproportion.columns.tolist()
    cols = cols[-2:] + cols[:-2]
    clusterproportion = clusterproportion[cols]  # rearrange columns to match report
    clusterproportion.columns = report.columns
    # generating dataframe with count of nan values
    a = pd.DataFrame(
        abs(
            report[report["Type"] == "count"].iloc[:, 2:].to_numpy()
            - clustersize.iloc[:, 2:].to_numpy()
        )
    )
    a["Features"] = 0
    a["Type"] = "# of nan"
    # filling values in order to match report
    a.Features = report[report["Type"] == "count"].Features.tolist()
    cols = a.columns.tolist()
    cols = cols[-2:] + cols[:-2]
    a = a[cols]  # rearrange columns to match report
    a.columns = report.columns  # rename columns to match report
    # drop count values except for cluster size
    report = report.drop(report[report.Type == "count"].index)
    # concat report with cluster size and nan values
    report = pd.concat([report, a, clustersize, clusterproportion], axis=0)
    report["Mark"] = report["Features"].isin(clustering_variables)
    cols = report.columns.tolist()
    cols = cols[0:2] + cols[-1:] + cols[2:-1]
    report = report[cols]
    sorter1 = {
        "ClusterSize": 9,
        "ClusterProportion": 8,
        "mean_with_zeros": 7,
        "mean_with_na": 6,
        "max": 5,
        "50%": 4,
        "min": 3,
        "25%": 2,
        "75%": 1,
        "# of nan": 0,
        "# > 0": -1,
        "sum_with_na": -2,
    }
    report = (
        report.assign(
            Sorter1=lambda x: x.Type.map(sorter1),
            Sorter2=lambda x: list(reversed(range(len(x)))),
        )
        .sort_values(["Sorter1", "Mark", "Sorter2"], ascending=False)
        .drop(["Sorter1", "Sorter2"], axis=1)
    )
    report.columns.name = ""
    report = report.reset_index()
    report = report.drop(columns=["index"])
    return report


if __name__ == "__main__":
    import doctest

    doctest.testmod()

===========================================================

"""
Implementation of a basic regression decision tree.
Input data set: The input data set must be 1-dimensional with continuous labels.
Output: The decision tree maps a real number input to a real number output.
"""

import numpy as np


class DecisionTree:
    def __init__(self, depth=5, min_leaf_size=5):
        self.depth = depth
        self.decision_boundary = 0
        self.left = None
        self.right = None
        self.min_leaf_size = min_leaf_size
        self.prediction = None

    def mean_squared_error(self, labels, prediction):
        """
        mean_squared_error:
        @param labels: a one-dimensional numpy array
        @param prediction: a floating point value
        return value: mean_squared_error calculates the error if prediction is used to
            estimate the labels
        >>> tester = DecisionTree()
        >>> test_labels = np.array([1,2,3,4,5,6,7,8,9,10])
        >>> test_prediction = float(6)
        >>> bool(tester.mean_squared_error(test_labels, test_prediction) == (
        ...     TestDecisionTree.helper_mean_squared_error_test(test_labels,
        ...         test_prediction)))
        True
        >>> test_labels = np.array([1,2,3])
        >>> test_prediction = float(2)
        >>> bool(tester.mean_squared_error(test_labels, test_prediction) == (
        ...     TestDecisionTree.helper_mean_squared_error_test(test_labels,
        ...         test_prediction)))
        True
        """
        if labels.ndim != 1:
            print("Error: Input labels must be one dimensional")

        return np.mean((labels - prediction) ** 2)

    def train(self, x, y):
        """
        train:
        @param x: a one-dimensional numpy array
        @param y: a one-dimensional numpy array.
        The contents of y are the labels for the corresponding X values

        train() does not have a return value

        Examples:
        1. Try to train when x & y are of same length & 1 dimensions (No errors)
        >>> dt = DecisionTree()
        >>> dt.train(np.array([10,20,30,40,50]),np.array([0,0,0,1,1]))

        2. Try to train when x is 2 dimensions
        >>> dt = DecisionTree()
        >>> dt.train(np.array([[1,2,3,4,5],[1,2,3,4,5]]),np.array([0,0,0,1,1]))
        Traceback (most recent call last):
            ...
        ValueError: Input data set must be one-dimensional

        3. Try to train when x and y are not of the same length
        >>> dt = DecisionTree()
        >>> dt.train(np.array([1,2,3,4,5]),np.array([[0,0,0,1,1],[0,0,0,1,1]]))
        Traceback (most recent call last):
            ...
        ValueError: x and y have different lengths

        4. Try to train when x & y are of the same length but different dimensions
        >>> dt = DecisionTree()
        >>> dt.train(np.array([1,2,3,4,5]),np.array([[1],[2],[3],[4],[5]]))
        Traceback (most recent call last):
            ...
        ValueError: Data set labels must be one-dimensional

        This section is to check that the inputs conform to our dimensionality
        constraints
        """
        if x.ndim != 1:
            raise ValueError("Input data set must be one-dimensional")
        if len(x) != len(y):
            raise ValueError("x and y have different lengths")
        if y.ndim != 1:
            raise ValueError("Data set labels must be one-dimensional")

        if len(x) < 2 * self.min_leaf_size:
            self.prediction = np.mean(y)
            return

        if self.depth == 1:
            self.prediction = np.mean(y)
            return

        best_split = 0
        min_error = self.mean_squared_error(x, np.mean(y)) * 2

        """
        loop over all possible splits for the decision tree. find the best split.
        if no split exists that is less than 2 * error for the entire array
        then the data set is not split and the average for the entire array is used as
        the predictor
        """
        for i in range(len(x)):
            if len(x[:i]) < self.min_leaf_size:  # noqa: SIM114
                continue
            elif len(x[i:]) < self.min_leaf_size:
                continue
            else:
                error_left = self.mean_squared_error(x[:i], np.mean(y[:i]))
                error_right = self.mean_squared_error(x[i:], np.mean(y[i:]))
                error = error_left + error_right
                if error < min_error:
                    best_split = i
                    min_error = error

        if best_split != 0:
            left_x = x[:best_split]
            left_y = y[:best_split]
            right_x = x[best_split:]
            right_y = y[best_split:]

            self.decision_boundary = x[best_split]
            self.left = DecisionTree(
                depth=self.depth - 1, min_leaf_size=self.min_leaf_size
            )
            self.right = DecisionTree(
                depth=self.depth - 1, min_leaf_size=self.min_leaf_size
            )
            self.left.train(left_x, left_y)
            self.right.train(right_x, right_y)
        else:
            self.prediction = np.mean(y)

        return

    def predict(self, x):
        """
        predict:
        @param x: a floating point value to predict the label of
        the prediction function works by recursively calling the predict function
        of the appropriate subtrees based on the tree's decision boundary
        """
        if self.prediction is not None:
            return self.prediction
        elif self.left or self.right is not None:
            if x >= self.decision_boundary:
                return self.right.predict(x)
            else:
                return self.left.predict(x)
        else:
            print("Error: Decision tree not yet trained")
            return None


class TestDecisionTree:
    """Decision Tres test class"""

    @staticmethod
    def helper_mean_squared_error_test(labels, prediction):
        """
        helper_mean_squared_error_test:
        @param labels: a one dimensional numpy array
        @param prediction: a floating point value
        return value: helper_mean_squared_error_test calculates the mean squared error
        """
        squared_error_sum = float(0)
        for label in labels:
            squared_error_sum += (label - prediction) ** 2

        return float(squared_error_sum / labels.size)


def main():
    """
    In this demonstration we're generating a sample data set from the sin function in
    numpy.  We then train a decision tree on the data set and use the decision tree to
    predict the label of 10 different test values. Then the mean squared error over
    this test is displayed.
    """
    x = np.arange(-1.0, 1.0, 0.005)
    y = np.sin(x)

    tree = DecisionTree(depth=10, min_leaf_size=10)
    tree.train(x, y)

    rng = np.random.default_rng()
    test_cases = (rng.random(10) * 2) - 1
    predictions = np.array([tree.predict(x) for x in test_cases])
    avg_error = np.mean((predictions - test_cases) ** 2)

    print("Test values: " + str(test_cases))
    print("Predictions: " + str(predictions))
    print("Average error: " + str(avg_error))


if __name__ == "__main__":
    main()
    import doctest

    doctest.testmod(name="mean_squarred_error", verbose=True)

==========================================================

import numpy as np
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor


class GradientBoostingClassifier:
    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1) -> None:
        """
        Initialize a GradientBoostingClassifier.

        Parameters:
        - n_estimators (int): The number of weak learners to train.
        - learning_rate (float): The learning rate for updating the model.

        Attributes:
        - n_estimators (int): The number of weak learners.
        - learning_rate (float): The learning rate.
        - models (list): A list to store the trained weak learners.
        """
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.models: list[tuple[DecisionTreeRegressor, float]] = []

    def fit(self, features: np.ndarray, target: np.ndarray) -> None:
        """
        Fit the GradientBoostingClassifier to the training data.

        Parameters:
        - features (np.ndarray): The training features.
        - target (np.ndarray): The target values.

        Returns:
        None

        >>> import numpy as np
        >>> from sklearn.datasets import load_iris
        >>> clf = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1)
        >>> iris = load_iris()
        >>> X, y = iris.data, iris.target
        >>> clf.fit(X, y)
        >>> # Check if the model is trained
        >>> len(clf.models) == 100
        True
        """
        for _ in range(self.n_estimators):
            # Calculate the pseudo-residuals
            residuals = -self.gradient(target, self.predict(features))
            # Fit a weak learner (e.g., decision tree) to the residuals
            model = DecisionTreeRegressor(max_depth=1)
            model.fit(features, residuals)
            # Update the model by adding the weak learner with a learning rate
            self.models.append((model, self.learning_rate))

    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Make predictions on input data.

        Parameters:
        - features (np.ndarray): The input data for making predictions.

        Returns:
        - np.ndarray: An array of binary predictions (-1 or 1).

        >>> import numpy as np
        >>> from sklearn.datasets import load_iris
        >>> clf = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1)
        >>> iris = load_iris()
        >>> X, y = iris.data, iris.target
        >>> clf.fit(X, y)
        >>> y_pred = clf.predict(X)
        >>> # Check if the predictions have the correct shape
        >>> y_pred.shape == y.shape
        True
        """
        # Initialize predictions with zeros
        predictions = np.zeros(features.shape[0])
        for model, learning_rate in self.models:
            predictions += learning_rate * model.predict(features)
        return np.sign(predictions)  # Convert to binary predictions (-1 or 1)

    def gradient(self, target: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
        """
        Calculate the negative gradient (pseudo-residuals) for logistic loss.

        Parameters:
        - target (np.ndarray): The target values.
        - y_pred (np.ndarray): The predicted values.

        Returns:
        - np.ndarray: An array of pseudo-residuals.

        >>> import numpy as np
        >>> clf = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1)
        >>> target = np.array([0, 1, 0, 1])
        >>> y_pred = np.array([0.2, 0.8, 0.3, 0.7])
        >>> residuals = clf.gradient(target, y_pred)
        >>> # Check if residuals have the correct shape
        >>> residuals.shape == target.shape
        True
        """
        return -target / (1 + np.exp(target * y_pred))


if __name__ == "__main__":
    iris = load_iris()
    X, y = iris.data, iris.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    clf = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {accuracy:.2f}")

====================================================

# XGBoost Classifier Example
import numpy as np
from matplotlib import pyplot as plt
from sklearn.datasets import load_iris
from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


def data_handling(data: dict) -> tuple:
    # Split dataset into features and target
    # data is features
    """
    >>> data_handling(({'data':'[5.1, 3.5, 1.4, 0.2]','target':([0])}))
    ('[5.1, 3.5, 1.4, 0.2]', [0])
    >>> data_handling(
    ...     {'data': '[4.9, 3.0, 1.4, 0.2], [4.7, 3.2, 1.3, 0.2]', 'target': ([0, 0])}
    ... )
    ('[4.9, 3.0, 1.4, 0.2], [4.7, 3.2, 1.3, 0.2]', [0, 0])
    """
    return (data["data"], data["target"])


def xgboost(features: np.ndarray, target: np.ndarray) -> XGBClassifier:
    """
    # THIS TEST IS BROKEN!! >>> xgboost(np.array([[5.1, 3.6, 1.4, 0.2]]), np.array([0]))
    XGBClassifier(base_score=0.5, booster='gbtree', callbacks=None,
                  colsample_bylevel=1, colsample_bynode=1, colsample_bytree=1,
                  early_stopping_rounds=None, enable_categorical=False,
                  eval_metric=None, gamma=0, gpu_id=-1, grow_policy='depthwise',
                  importance_type=None, interaction_constraints='',
                  learning_rate=0.300000012, max_bin=256, max_cat_to_onehot=4,
                  max_delta_step=0, max_depth=6, max_leaves=0, min_child_weight=1,
                  missing=nan, monotone_constraints='()', n_estimators=100,
                  n_jobs=0, num_parallel_tree=1, predictor='auto', random_state=0,
                  reg_alpha=0, reg_lambda=1, ...)
    """
    classifier = XGBClassifier()
    classifier.fit(features, target)
    return classifier


def main() -> None:
    """
    >>> main()

    Url for the algorithm:
    https://xgboost.readthedocs.io/en/stable/
    Iris type dataset is used to demonstrate algorithm.
    """

    # Load Iris dataset
    iris = load_iris()
    features, targets = data_handling(iris)
    x_train, x_test, y_train, y_test = train_test_split(
        features, targets, test_size=0.25
    )

    names = iris["target_names"]

    # Create an XGBoost Classifier from the training data
    xgboost_classifier = xgboost(x_train, y_train)

    # Display the confusion matrix of the classifier with both training and test sets
    ConfusionMatrixDisplay.from_estimator(
        xgboost_classifier,
        x_test,
        y_test,
        display_labels=names,
        cmap="Blues",
        normalize="true",
    )
    plt.title("Normalized Confusion Matrix - IRIS Dataset")
    plt.show()


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
    main()

=================================

# XGBoost Regressor Example
import numpy as np
from sklearn.datasets import fetch_california_housing
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


def data_handling(data: dict) -> tuple:
    # Split dataset into features and target.  Data is features.
    """
    >>> data_handling((
    ...  {'data':'[ 8.3252 41. 6.9841269 1.02380952  322. 2.55555556   37.88 -122.23 ]'
    ...  ,'target':([4.526])}))
    ('[ 8.3252 41. 6.9841269 1.02380952  322. 2.55555556   37.88 -122.23 ]', [4.526])
    """
    return (data["data"], data["target"])


def xgboost(
    features: np.ndarray, target: np.ndarray, test_features: np.ndarray
) -> np.ndarray:
    """
    >>> xgboost(np.array([[ 2.3571 ,   52. , 6.00813008, 1.06775068,
    ...    907. , 2.45799458,   40.58 , -124.26]]),np.array([1.114]),
    ... np.array([[1.97840000e+00,  3.70000000e+01,  4.98858447e+00,  1.03881279e+00,
    ...    1.14300000e+03,  2.60958904e+00,  3.67800000e+01, -1.19780000e+02]]))
    array([[1.1139996]], dtype=float32)
    """
    xgb = XGBRegressor(
        verbosity=0, random_state=42, tree_method="exact", base_score=0.5
    )
    xgb.fit(features, target)
    # Predict target for test data
    predictions = xgb.predict(test_features)
    predictions = predictions.reshape(len(predictions), 1)
    return predictions


def main() -> None:
    """
    The URL for this algorithm
    https://xgboost.readthedocs.io/en/stable/
    California house price dataset is used to demonstrate the algorithm.

    Expected error values:
    Mean Absolute Error: 0.30957163379906033
    Mean Square Error: 0.22611560196662744
    """
    # Load California house price dataset
    california = fetch_california_housing()
    data, target = data_handling(california)
    x_train, x_test, y_train, y_test = train_test_split(
        data, target, test_size=0.25, random_state=1
    )
    predictions = xgboost(x_train, y_train, x_test)
    # Error printing
    print(f"Mean Absolute Error: {mean_absolute_error(y_test, predictions)}")
    print(f"Mean Square Error: {mean_squared_error(y_test, predictions)}")


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
    main()

==================================================

"""
Create a Long Short Term Memory (LSTM) network model
An LSTM is a type of Recurrent Neural Network (RNN) as discussed at:
* https://colah.github.io/posts/2015-08-Understanding-LSTMs
* https://en.wikipedia.org/wiki/Long_short-term_memory
"""

import numpy as np
import pandas as pd
from keras.layers import LSTM, Dense
from keras.models import Sequential
from sklearn.preprocessing import MinMaxScaler

if __name__ == "__main__":
    """
    First part of building a model is to get the data and prepare
    it for our model. You can use any dataset for stock prediction
    make sure you set the price column on line number 21.  Here we
    use a dataset which have the price on 3rd column.
    """
    sample_data = pd.read_csv("sample_data.csv", header=None)
    len_data = sample_data.shape[:1][0]
    # If you're using some other dataset input the target column
    actual_data = sample_data.iloc[:, 1:2]
    actual_data = actual_data.to_numpy().reshape(len_data, 1)
    actual_data = MinMaxScaler().fit_transform(actual_data)
    look_back = 10
    forward_days = 5
    periods = 20
    division = len_data - periods * look_back
    train_data = actual_data[:division]
    test_data = actual_data[division - look_back :]
    train_x, train_y = [], []
    test_x, test_y = [], []

    for i in range(len(train_data) - forward_days - look_back + 1):
        train_x.append(train_data[i : i + look_back])
        train_y.append(train_data[i + look_back : i + look_back + forward_days])
    for i in range(len(test_data) - forward_days - look_back + 1):
        test_x.append(test_data[i : i + look_back])
        test_y.append(test_data[i + look_back : i + look_back + forward_days])
    x_train = np.array(train_x)
    x_test = np.array(test_x)
    y_train = np.array([list(i.ravel()) for i in train_y])
    y_test = np.array([list(i.ravel()) for i in test_y])

    model = Sequential()
    model.add(LSTM(128, input_shape=(look_back, 1), return_sequences=True))
    model.add(LSTM(64, input_shape=(128, 1)))
    model.add(Dense(forward_days))
    model.compile(loss="mean_squared_error", optimizer="adam")
    history = model.fit(
        x_train, y_train, epochs=150, verbose=1, shuffle=True, batch_size=4
    )
    pred = model.predict(x_test)

================================================


"""
this is code for forecasting
but I modified it and used it for safety checker of data
for ex: you have an online shop and for some reason some data are
missing (the amount of data that u expected are not supposed to be)
        then we can use it
*ps : 1. ofc we can use normal statistic method but in this case
         the data is quite absurd and only a little^^
      2. ofc u can use this and modified it for forecasting purpose
         for the next 3 months sales or something,
         u can just adjust it for ur own purpose
"""

from warnings import simplefilter

import numpy as np
import pandas as pd
from sklearn.preprocessing import Normalizer
from sklearn.svm import SVR
from statsmodels.tsa.statespace.sarimax import SARIMAX


def linear_regression_prediction(
    train_dt: list, train_usr: list, train_mtch: list, test_dt: list, test_mtch: list
) -> float:
    """
    First method: linear regression
    input : training data (date, total_user, total_event) in list of float
    output : list of total user prediction in float
    >>> n = linear_regression_prediction([2,3,4,5], [5,3,4,6], [3,1,2,4], [2,1], [2,2])
    >>> bool(abs(n - 5.0) < 1e-6)  # Checking precision because of floating point errors
    True
    """
    x = np.array([[1, item, train_mtch[i]] for i, item in enumerate(train_dt)])
    y = np.array(train_usr)
    beta = np.dot(np.dot(np.linalg.inv(np.dot(x.transpose(), x)), x.transpose()), y)
    return abs(beta[0] + test_dt[0] * beta[1] + test_mtch[0] + beta[2])


def sarimax_predictor(train_user: list, train_match: list, test_match: list) -> float:
    """
    second method: Sarimax
    sarimax is a statistic method which using previous input
    and learn its pattern to predict future data
    input : training data (total_user, with exog data = total_event) in list of float
    output : list of total user prediction in float
    >>> sarimax_predictor([4,2,6,8], [3,1,2,4], [2])
    6.6666671111109626
    """
    # Suppress the User Warning raised by SARIMAX due to insufficient observations
    simplefilter("ignore", UserWarning)
    order = (1, 2, 1)
    seasonal_order = (1, 1, 1, 7)
    model = SARIMAX(
        train_user, exog=train_match, order=order, seasonal_order=seasonal_order
    )
    model_fit = model.fit(disp=False, maxiter=600, method="nm")
    result = model_fit.predict(1, len(test_match), exog=[test_match])
    return float(result[0])


def support_vector_regressor(x_train: list, x_test: list, train_user: list) -> float:
    """
    Third method: Support vector regressor
    svr is quite the same with svm(support vector machine)
    it uses the same principles as the SVM for classification,
    with only a few minor differences and the only different is that
    it suits better for regression purpose
    input : training data (date, total_user, total_event) in list of float
    where x = list of set (date and total event)
    output : list of total user prediction in float
    >>> support_vector_regressor([[5,2],[1,5],[6,2]], [[3,2]], [2,1,4])
    1.634932078116079
    """
    regressor = SVR(kernel="rbf", C=1, gamma=0.1, epsilon=0.1)
    regressor.fit(x_train, train_user)
    y_pred = regressor.predict(x_test)
    return float(y_pred[0])


def interquartile_range_checker(train_user: list) -> float:
    """
    Optional method: interquatile range
    input : list of total user in float
    output : low limit of input in float
    this method can be used to check whether some data is outlier or not
    >>> interquartile_range_checker([1,2,3,4,5,6,7,8,9,10])
    2.8
    """
    train_user.sort()
    q1 = np.percentile(train_user, 25)
    q3 = np.percentile(train_user, 75)
    iqr = q3 - q1
    low_lim = q1 - (iqr * 0.1)
    return float(low_lim)


def data_safety_checker(list_vote: list, actual_result: float) -> bool:
    """
    Used to review all the votes (list result prediction)
    and compare it to the actual result.
    input : list of predictions
    output : print whether it's safe or not
    >>> data_safety_checker([2, 3, 4], 5.0)
    False
    """
    safe = 0
    not_safe = 0

    if not isinstance(actual_result, float):
        raise TypeError("Actual result should be float. Value passed is a list")

    for i in list_vote:
        if i > actual_result:
            safe = not_safe + 1
        elif abs(abs(i) - abs(actual_result)) <= 0.1:
            safe += 1
        else:
            not_safe += 1
    return safe > not_safe


if __name__ == "__main__":
    """
    data column = total user in a day, how much online event held in one day,
    what day is that(sunday-saturday)
    """
    data_input_df = pd.read_csv("ex_data.csv")

    # start normalization
    normalize_df = Normalizer().fit_transform(data_input_df.values)
    # split data
    total_date = normalize_df[:, 2].tolist()
    total_user = normalize_df[:, 0].tolist()
    total_match = normalize_df[:, 1].tolist()

    # for svr (input variable = total date and total match)
    x = normalize_df[:, [1, 2]].tolist()
    x_train = x[: len(x) - 1]
    x_test = x[len(x) - 1 :]

    # for linear regression & sarimax
    train_date = total_date[: len(total_date) - 1]
    train_user = total_user[: len(total_user) - 1]
    train_match = total_match[: len(total_match) - 1]

    test_date = total_date[len(total_date) - 1 :]
    test_user = total_user[len(total_user) - 1 :]
    test_match = total_match[len(total_match) - 1 :]

    # voting system with forecasting
    res_vote = [
        linear_regression_prediction(
            train_date, train_user, train_match, test_date, test_match
        ),
        sarimax_predictor(train_user, train_match, test_match),
        support_vector_regressor(x_train, x_test, train_user),
    ]

    # check the safety of today's data
    not_str = "" if data_safety_checker(res_vote, test_user[0]) else "not "
    print(f"Today's data is {not_str}safe.")

