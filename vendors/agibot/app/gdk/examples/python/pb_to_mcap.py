      
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import struct
import argparse
from pathlib import Path
import importlib
import datetime
from importlib.metadata import version, PackageNotFoundError

# 话题名称到消息类型的默认映射
TOPIC_MESSAGE_MAP = {
    # -------------------G2 -----------------------
    "/hal/joint_state": "genie_msgs_pb.msg.JointState_pb2.JointState",
    "/hal/joint_cmd": "genie_msgs_pb.msg.JointCommand_pb2.JointCommand",
    "/wbc/joint_position_control": "genie_msgs_pb.msg.JointPositionControl_pb2.JointPositionControl",
}

class PbdatToMcapConverter:
    """PBDAT到MCAP转换器 - 命令行版本"""
    
    def __init__(self):
        self.topic_message_map = TOPIC_MESSAGE_MAP
        
    def check_dependencies(self):
        print("checking deps...")
        
        # 检查genie-msgs-pb
        genie_version = self.get_package_version('genie-msgs-pb')
        if not genie_version:
            print("genie-msgs-pb: not installed")
            return False
        else:
            print(f"genie-msgs-pb: v{genie_version}")
        
        # 检查protobuf版本
        protobuf_version = self.get_package_version('protobuf')
        required_protobuf = "5.28.3"
        if not protobuf_version:
            print(f"protobuf: not installed (required v{required_protobuf})")
            return False
        elif protobuf_version != required_protobuf:
            print(f"protobuf: v{protobuf_version} (required v{required_protobuf})")
            return False
        else:
            print(f"protobuf: v{protobuf_version}")
        
        # 检查mcap-protobuf-support版本
        mcap_version = self.get_package_version('mcap-protobuf-support')
        min_version, max_version = "0.2.0", "0.5.3"
        if not mcap_version:
            print(f"mcap-protobuf-support: not installed (required v{min_version}-{max_version})")
            return False
        elif not self.is_version_in_range(mcap_version, min_version, max_version):
            print(f"mcap-protobuf-support: v{mcap_version} (required v{min_version}-{max_version})")
            return False
        else:
            print(f"mcap-protobuf-support: v{mcap_version}")
        
        print("all deps checked successfully!")
        return True
    
    def get_package_version(self, package_name):
        """获取已安装包的版本信息"""
        try:
            return version(package_name)
        except PackageNotFoundError:
            return None
        except Exception:
            try:
                import pkg_resources
                return pkg_resources.get_distribution(package_name).version
            except Exception:
                return None
    
    def is_version_in_range(self, version, min_version, max_version):
        """检查版本是否在指定范围内"""
        try:
            def version_tuple(v):
                return tuple(map(int, (v.split("."))))
            
            current_ver = version_tuple(version)
            min_ver = version_tuple(min_version)
            max_ver = version_tuple(max_version)
            
            return min_ver <= current_ver <= max_ver
        except (ValueError, AttributeError):
            return False
    
    def extract_topic_from_filename(self, filename):
        """从文件名提取话题名称"""
        base_name = Path(filename).stem
        
        # 如果文件名以'-'开头，去掉开头的'-'
        if base_name.startswith('-'):
            base_name = base_name[1:]
        
        # 将'-'替换为'/'，并确保以'/'开头
        topic = '/' + base_name.replace('-', '/')
        print(f"extracted topic: {topic}")
        return topic
    
    def get_message_type_for_topic(self, topic):
        """根据话题名称获取消息类型"""
        return self.topic_message_map.get(topic, "")
    
    def convert_single_pbdat(self, pbdat_path, mcap_writer, topic, message_type):
        """转换单个PBDAT文件"""
        # 动态导入消息类型
        module_path, class_name = message_type.rsplit('.', 1)
        
        try:
            module = importlib.import_module(module_path)
            message_class = getattr(module, class_name)
            print(f"successfully imported message type: {message_type}")
        except (ImportError, AttributeError) as e:
            raise Exception(f"failed to import message type {message_type}: {str(e)}")
        
        verbose = True
        with open(pbdat_path, "rb") as in_f:
            # 读总帧数
            total_frames = struct.unpack("q", in_f.read(8))[0]
            print(f"processing {pbdat_path}: total frames: {total_frames}")
            
            frame_count = 0
            # 循环每帧
            while in_f.tell() < os.path.getsize(pbdat_path):
                try:
                    # 读取ptp值
                    ptp_value = struct.unpack("q", in_f.read(8))[0]
                    # 跳过3个reserved字段
                    in_f.seek(8 * 3, os.SEEK_CUR)
                    # 读帧长度和数据
                    frame_size = struct.unpack("q", in_f.read(8))[0]
                    data = in_f.read(frame_size)
                    
                    # 解析消息
                    msg = message_class()
                    msg.ParseFromString(data)
                    
                    if verbose:
                        print("{} topic uses PTP timestamp: first frame timestamp is {}".format(
                            topic, 
                            datetime.datetime.fromtimestamp(ptp_value/1_000_000_000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                        ))
                        verbose = False
                    ts = ptp_value
                        
                    # 写入MCAP
                    mcap_writer.write_message(
                        topic=topic,
                        message=msg,
                        log_time=ts,
                        publish_time=ts,
                    )
                    
                    frame_count += 1
                    
                except Exception as e:
                    print(f"error processing frame {frame_count} in {pbdat_path}: {str(e)}")
                    continue
                    
            print(f"successfully processed {frame_count} frames from {pbdat_path}")
            return frame_count
    
    def convert_files(self, pbdat_files, output_mcap_path):
        """转换多个PBDAT文件到单个MCAP文件"""
        from mcap_protobuf.writer import Writer as ProtobufWriter
        
        print(f"starting conversion of {len(pbdat_files)} PBDAT files to {output_mcap_path}")
        
        total_frames = 0
        with open(output_mcap_path, "wb") as out_f, ProtobufWriter(out_f) as mcap_writer:
            for pbdat_file in pbdat_files:
                filename = Path(pbdat_file).name
                topic = self.extract_topic_from_filename(pbdat_file)
                message_type = self.get_message_type_for_topic(topic)
                
                if not message_type:
                    print(f"skipping file {filename}: no corresponding topic mapping (extracted topic: {topic})")
                    continue
                
                print(f"converting file: {filename} -> topic: {topic}")
                try:
                    frames = self.convert_single_pbdat(pbdat_file, mcap_writer, topic, message_type)
                    total_frames += frames
                except Exception as e:
                    print(f"failed to convert file {filename}: {str(e)}")
                    continue
        
        print(f"conversion completed! successfully processed {total_frames} frames")
        return total_frames

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PBDAT到MCAP转换工具 - 命令行版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 转换单个文件
  python3 pb_to_mcap_cli.py -i file1.pbdat -o output.mcap
  
  # 转换多个文件
  python3 pb_to_mcap_cli.py -i file1.pbdat file2.pbdat -o output.mcap
  
        """
    )
    
    parser.add_argument('-i', '--input', required=True,
                       help='directory of pbdat files')
    parser.add_argument('-o', '--output', required=True,
                       help='output mcap file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='verbose output')
    
    args = parser.parse_args()
    
    # 创建转换器实例
    converter = PbdatToMcapConverter()
    
    # 检查依赖包
    if not converter.check_dependencies():
        print("\n dependency check failed, please install missing packages:")
        print("   pip install genie-msgs-pb protobuf==5.28.3 'mcap-protobuf-support>=0.2.0,<0.5.3'")
        sys.exit(1)
    
    # get pbdat files from input directory
    pbdat_files = [os.path.join(args.input, file) for file in os.listdir(args.input) if file.endswith('.pbdat')]
    output_path = os.path.join(args.output, 'all_data.mcap')
    
    # 执行转换
    try:
        total_frames = converter.convert_files(
            pbdat_files, 
            output_path, 
        )
        
        if total_frames > 0:
            print(f"\nconversion completed successfully!")
            print(f"statistics:")
            print(f"   - input files: {len(pbdat_files)}")
            print(f"   - output file: {output_path}")
            print(f"   - total frames: {total_frames}")
        else:
            print("warning: no data frames processed")
            sys.exit(1)
            
    except Exception as e:
        print(f"error during conversion: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

    