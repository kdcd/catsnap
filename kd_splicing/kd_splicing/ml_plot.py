import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve
from sklearn.metrics import auc
from sklearn.preprocessing import label_binarize
from scipy import interp

def roc(y_true, y_probas, title='ROC Curves',
                   plot_micro=True, plot_macro=True, classes_to_plot=None,
                   ax=None, figsize=None, cmap='nipy_spectral',
                   title_fontsize="large", text_fontsize="medium"):
    y_true = np.array(y_true)
    y_probas = np.array(y_probas)

    classes = classes_to_plot
    probas = y_probas

    if classes_to_plot is None:
        classes_to_plot = classes

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    ax.set_title(title, fontsize=title_fontsize)

    fpr_dict = dict()
    tpr_dict = dict()

    for i, to_plot in enumerate(classes_to_plot):
        fpr_dict[i], tpr_dict[i], _ = roc_curve(y_true, probas[:, i])
        if to_plot:
            roc_auc = auc(fpr_dict[i], tpr_dict[i])
            color = plt.cm.get_cmap(cmap)(float(i) / len(classes))
            ax.plot(fpr_dict[i], tpr_dict[i], lw=2, color=color,
                    label='{0} (area = {1:0.2f})'
                          ''.format(classes[i], roc_auc))

    # if plot_micro:
    #     binarized_y_true = label_binarize(y_true, classes=classes)
    #     if len(classes) == 2:
    #         binarized_y_true = np.hstack(
    #             (1 - binarized_y_true, binarized_y_true))
    #     fpr, tpr, _ = roc_curve(binarized_y_true.ravel(), probas.ravel())
    #     roc_auc = auc(fpr, tpr)
    #     ax.plot(fpr, tpr,
    #             label='micro-average ROC curve '
    #                   '(area = {0:0.2f})'.format(roc_auc),
    #             color='deeppink', linestyle=':', linewidth=4)

    # if plot_macro:
    #     # Compute macro-average ROC curve and ROC area
    #     # First aggregate all false positive rates
    #     all_fpr = np.unique(np.concatenate([fpr_dict[x] for x in range(len(classes))]))

    #     # Then interpolate all ROC curves at this points
    #     mean_tpr = np.zeros_like(all_fpr)
    #     for i in range(len(classes)):
    #         mean_tpr += interp(all_fpr, fpr_dict[i], tpr_dict[i])

    #     # Finally average it and compute AUC
    #     mean_tpr /= len(classes)
    #     roc_auc = auc(all_fpr, mean_tpr)

    #     ax.plot(all_fpr, mean_tpr,
    #             label='macro-average ROC curve '
    #                   '(area = {0:0.2f})'.format(roc_auc),
    #             color='navy', linestyle=':', linewidth=4)

    ax.plot([0, 1], [0, 1], 'k--', lw=2)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=text_fontsize)
    ax.set_ylabel('True Positive Rate', fontsize=text_fontsize)
    ax.tick_params(labelsize=text_fontsize)
    ax.legend(loc='lower right', fontsize=text_fontsize)
    return ax