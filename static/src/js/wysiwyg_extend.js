odoo.define("blogcreator.wysiwyg_extend", function (require) {
  "use strict";

  var core = require("web.core");
  var Wysiwyg = require("web_editor.wysiwyg");
  var Dialog = require("web.Dialog");
  var _t = core._t;

  Wysiwyg.include({
    /**
     * @override
     */
    _getDefaultToolbarButtons: function () {
      var toolbar = this._super.apply(this, arguments);
      alert("wysiwyg_extend");

      // Thêm nút mới vào toolbar
      toolbar.push({
        id: "blogcreator-image",
        title: _t("Chèn hình ảnh từ thư viện"),
        icon: "fa fa-file-image-o",
        callback: this._onBlogCreatorImageClick.bind(this),
      });

      return toolbar;
    },

    /**
     * Xử lý sự kiện click vào nút chèn hình ảnh
     * @private
     */
    _onBlogCreatorImageClick: function () {
      var self = this;

      // Tạo dialog chọn hình ảnh
      this._rpc({
        model: "ir.attachment",
        method: "search_read",
        domain: [
          ["res_model", "=", "blogcreator.note"],
          ["mimetype", "ilike", "image"],
        ],
        fields: ["id", "name", "datas", "mimetype"],
        limit: 30,
      }).then(function (attachments) {
        var $content = $('<div class="row"></div>');

        if (!attachments.length) {
          $content.append(
            $(
              '<div class="col-12 text-center"><p>Không có hình ảnh nào trong thư viện</p></div>'
            )
          );
        }

        // Hiển thị các hình ảnh
        _.each(attachments, function (attachment) {
          var $col = $('<div class="col-3 mb-3"></div>');
          var $img = $(
            '<img class="img-thumbnail img-fluid cursor-pointer"/>'
          ).attr(
            "src",
            "data:" + attachment.mimetype + ";base64," + attachment.datas
          );
          var $name = $('<p class="text-center mb-0"></p>').text(
            attachment.name
          );

          $col.append($img).append($name);
          $content.append($col);

          $img.on("click", function () {
            var imgUrl = "/web/image/" + attachment.id;
            self.odooEditor.execCommand(
              "insertHTML",
              '<img src="' + imgUrl + '" alt="' + attachment.name + '"/>'
            );
            dialog.close();
          });
        });

        var dialog = new Dialog(self, {
          title: _t("Chọn hình ảnh từ thư viện"),
          size: "large",
          $content: $content,
          buttons: [
            {
              text: _t("Đóng"),
              close: true,
            },
          ],
        });

        dialog.open();
      });
    },
  });
});
