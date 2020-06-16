from PyQt5.QtWidgets import QListWidgetItem, QMessageBox, QWidget

from brainframe.api import bf_codecs, bf_errors
from brainframe.client.api_utils import api
from brainframe.client.ui.resources import QTAsyncWorker
from brainframe.client.ui.resources.ui_elements.widgets.dialogs import \
    WorkingIndicator
from .license_dialog_ui import _LicenseDialogUI
from .product_sidebar.product_widget import ProductWidget

LICENSE_DOCS_LINK = "https://aotu.ai/docs/user_guide/server_setup/" \
                    "#getting-a-license"


class LicenseDialog(_LicenseDialogUI):
    BRAINFRAME_PRODUCT_NAME = "BrainFrame"

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._init_signals()

        self._init_products()

    @classmethod
    def show_dialog(cls, parent):
        dialog = cls(parent)

        dialog.resize(900, 500)

        dialog.exec_()

    def _init_signals(self) -> None:
        self.product_sidebar.currentItemChanged.connect(self.change_product)

        self.license_details.license_text_update.connect(
            self.send_update_license_text)

    def _init_products(self):
        def on_success(license_info: bf_codecs.LicenseInfo):
            icon_path = ":/icons/capsule_toolbar"
            self.product_sidebar.add_product(
                self.BRAINFRAME_PRODUCT_NAME, icon_path, license_info)

            # BrainFrame product should always be first in list
            self.product_sidebar.setCurrentRow(0)

        def on_error():
            pass

        QTAsyncWorker(self, api.get_license_info,
                      on_success=on_success, on_error=on_error) \
            .start()

        # TODO: Also get capsule information if that's ever added

    def change_product(self, item: QListWidgetItem) -> None:
        widget: ProductWidget = self.product_sidebar.itemWidget(item)

        self.license_details.set_product(widget.product_name,
                                         widget.license_info)

    def send_update_license_text(self, license_key: str):
        # TODO: Support more than BrainFrame license (if we ever support
        #       capsule licensing)

        working_indicator = WorkingIndicator(self)
        working_indicator.setLabelText(self.tr("Uploading license..."))
        working_indicator.show()

        def on_success(license_info: bf_codecs.LicenseInfo):
            self.update_license_info("BrainFrame", license_info)
            working_indicator.cancel()

        def on_error(exc: BaseException):
            working_indicator.cancel()
            self._handle_update_license_error(exc)

        QTAsyncWorker(self, api.set_license_key, f_args=(license_key,),
                      on_success=on_success,
                      on_error=on_error) \
            .start()

    def update_license_info(self, product_name: str,
                            license_info: bf_codecs.LicenseInfo) -> None:

        self.product_sidebar.update_license_info(product_name, license_info)

        # Only change the license details if the product is already displayed
        if self.license_details.product_name == product_name:
            self.license_details.set_product(product_name, license_info)

    def _handle_update_license_error(self, exc: BaseException):
        if isinstance(exc, bf_errors.LicenseInvalidError):

            message_title = self.tr("Invalid License Format")
            message = self.tr(
                "The provided license has an invalid format. Please "
                "<a href='{license_docs_link}'>download a new license</a>.") \
                .format(license_docs_link=LICENSE_DOCS_LINK)
        else:
            raise exc

        QMessageBox.information(self, message_title, message)
