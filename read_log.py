import re
from tabulate import tabulate








# #patern này ta thấy là nếu cái nào ta để trong ( ) là nó sẽ đối chiếu với chuỗi phía trong, từ đó lấy ra, ở trong mỗi dấu ( ) được gọi là 1 group
# patern = r"(\bC\d+-\d+\b).*?(\[T: 0\]-\[ADC: \d+\]).*?(\[T: 1\]-\[ADC: \d+\]).*?(\[T: 2\]-\[ADC: \d+\])"

# patern này thì dấu ( ) chỉ chứa trong \d+ nên nó chỉ lấy cái số thoi và nó vẫn là 1 group
# patern = r"(\bC\d+-\d+\b).*?\[T: 0\]-\[ADC: (\d+)\].*?\[T: 1\]-\[ADC: (\d+)\].*?\[T: 2\]-\[ADC: (\d+)\]"

#Ở đây sẽ trả về 5 group là 5 cái là 5 cái trong (), là hàng, côt, giá trị ADC trả về lần 1,2,33
#patern = r"C(\d+)-(\d+).*?\[T: 0\]-\[ADC: (\d+)\].*?\[T: 1\]-\[ADC: (\d+)\].*?\[T: 2\]-\[ADC: (\d+)\]

#Nhưng các cách regex trên đều mắc lỗi là nếu mà cảm biến không gửi về đủ 3 cái thì nó sẽ không nhận về, nó sẽ báo lỗi
#Khắc phục bằng cách viết regex bên dưới, dấu ? là để đánh dấu nó có thể có hay không


  

#patern = r"C(\d+)-(\d+).*?(\d+).*?(\d+).*?(\d+)"

'''
PHÂN TÍCH CHUỖI KHI ĐỌC VỀ
'''
output = [0,0,0,0,0,0]
sensor_value = [[None]*6 for _ in range(6)]
def process_data(log_line,output):
    patern = r"C(\d+)-(\d+)"\
            r".*?\[T: 0\]-\[ADC: (\d+)\]"\
            r"(?:.*?\[T: 1\]-\[ADC: (\d+)\])?"\
            r"(?:.*?\[T: 2\]-\[ADC: (\d+)\])?"\
            r"(?:.*?\[T: 3\]-\[ADC: (\d+)\])?"
    match = re.search(patern, log_line)

    if match:
        output = list(match.groups())
        output = [0 if x is None else x for x in output]
        output = list(map(int,output))
        sensor_value[output[0]-1][output[1]-1] = avarage(output)
        return sensor_value     
    else:
        print("Không tìm thấy dữ liệu cảm biến!")


#Tính giá trị trung bình, xét điều kiện lớn hơn 2 là do bỏ 2 giá trị đầu, kiểm tra những số khác 0 và chỉ lấy trung bình những số đó
def avarage(output):
    a = 0
    sum = 0
    for i,value in enumerate(output):
        if (i > 1) and (value != 0):
            sum += value
            a+=1
        continue
    return sum/a





def send_to_matrix(sensor_value,output):
    with open("test.log", "r", encoding="utf-8") as file:
        for log_line in file:
            if "ADC" in log_line:
                process_data(log_line,output)
            
                




# def format_table(self,x,y):
#     self.formatted = []
#     table_str = tabulate(sensor_value,tablefmt="grid").split("\n")
#     semaphore = 0
#     row_indx, col_indx = 0,0
#     for i,row in enumerate(table_str):
#         if i % 2 == 0:
#             for char in row:
#                 self.formatted.append(("fg:white",char))
#             self.formatted.append(("fg:white","\n"))
#         if i % 2 != 0:
#             col_indx = 0
#             semaphore = 0
#             for char in row:
#                 if char.isdigit() or char == "." or " ":
#                     if row_indx == (x-1) and col_indx == (y-1):
#                         self.formatted.append(("bg:yellow",char))
#                     else:
#                         self.formatted.append(("fg:white",char))              
#                 else:
#                     self.formatted.append(("fg:white",char))
#                     semaphore +=1
#                     if semaphore > 1:
#                         col_indx +=1
#             self.formatted.append(("fg:white","\n"))
#             row_indx +=1
#     print(f"TABULATE: \n{self.formatted}")

send_to_matrix(sensor_value,output)
table_str = tabulate(sensor_value,tablefmt="grid").split("\n")
print(table_str[1][0])

