Name:		asm-jdk-bridge
Version:	0.0.14
Release:	1
Summary:	ASM adapters for the OpenJDK class file API
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/raphw/asm-jdk-bridge
Source0:	https://github.com/raphw/asm-jdk-bridge/archive/refs/tags/asm-jdk-bridge-parent-%{version}.tar.gz
BuildArch:	noarch
BuildRequires:	python
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildRequires:	mvn(org.ow2.asm:asm)
BuildSystem:	maven
BuildOption(install):	--file-name asm-jdk-bridge

%description
Adapters between ASM visitors and the OpenJDK class file API.
The base classes are Java 8 stubs. Java 24 and newer load the real
implementation from the multi-release jar.

%prep
%setup -q -n asm-jdk-bridge-asm-jdk-bridge-parent-%{version}
rm -rf src pom.xml
cp -a asm-jdk-bridge/src src
rm -rf asm-jdk-bridge asm-jdk-bridge-test
# The Java 9 module-info requires org.objectweb.asm. The system ASM
# jar is an automatic module named asm, so that descriptor does not
# resolve. The jar stays an automatic module under its upstream name.
rm -rf src/main/java-9
python - %{version} <<'PY'
import sys
from pathlib import Path
version = sys.argv[1]
Path("pom.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>codes.rafael.asmjdkbridge</groupId>
  <artifactId>asm-jdk-bridge</artifactId>
  <version>{version}</version>
  <packaging>jar</packaging>
  <name>ASM to OpenJDK Class API bridge</name>
  <description>Adapters between ASM visitors and the OpenJDK class file API, packaged without a parent POM.</description>
  <url>https://github.com/raphw/asm-jdk-bridge</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <maven.compiler.release>8</maven.compiler.release>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.ow2.asm</groupId>
      <artifactId>asm</artifactId>
      <version>9.11.1</version>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.12.1</version>
        <executions>
          <execution>
            <id>java24-compile</id>
            <phase>process-classes</phase>
            <goals>
              <goal>compile</goal>
            </goals>
            <configuration>
              <release>24</release>
              <compileSourceRoots>
                <compileSourceRoot>${{project.basedir}}/src/main/java-24</compileSourceRoot>
              </compileSourceRoots>
              <outputDirectory>${{project.build.outputDirectory}}/META-INF/versions/24</outputDirectory>
            </configuration>
          </execution>
        </executions>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-jar-plugin</artifactId>
        <version>3.3.0</version>
        <configuration>
          <archive>
            <manifestEntries>
              <Multi-Release>true</Multi-Release>
              <Automatic-Module-Name>codes.rafael.asmjdkbridge</Automatic-Module-Name>
            </manifestEntries>
          </archive>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
''', encoding="utf-8")
text = Path("pom.xml").read_text(encoding="utf-8")
if text.count("<version>0.0.14</version>") != 1 or "<version>9.11.1</version>" not in text:
    raise SystemExit("pom versions changed")
if "<release>24</release>" not in text or "<maven.compiler.release>8</maven.compiler.release>" not in text:
    raise SystemExit("compiler release changed")
if "java-24" not in text or "Multi-Release" not in text:
    raise SystemExit("multi-release build was dropped")
for needle in ("<parent>", "junit", "SNAPSHOT", "<source>", "<target>", "felix", "oss-parent", "module-info"):
    if needle in text:
        raise SystemExit("pom still contains " + needle)
PY

%build -a
python - <<'PY'
import zipfile
from pathlib import Path
jars = list(Path("target").glob("asm-jdk-bridge-*.jar"))
if len(jars) != 1:
    raise SystemExit("expected one jar, found " + " ".join(str(p) for p in jars))
with zipfile.ZipFile(jars[0]) as zf:
    names = set(zf.namelist())
    need = [
        "codes/rafael/asmjdkbridge/ProbingClassReader.class",
        "codes/rafael/asmjdkbridge/ProbingClassWriter.class",
        "codes/rafael/asmjdkbridge/ProbingResolver.class",
        "codes/rafael/asmjdkbridge/JdkClassReader.class",
        "codes/rafael/asmjdkbridge/JdkClassWriter.class",
        "META-INF/versions/24/codes/rafael/asmjdkbridge/JdkClassReader.class",
        "META-INF/versions/24/codes/rafael/asmjdkbridge/JdkClassWriter.class",
        "META-INF/versions/24/codes/rafael/asmjdkbridge/AsmAttribute.class",
        "META-INF/versions/24/codes/rafael/asmjdkbridge/AsmWrappedAttribute.class",
    ]
    missing = [name for name in need if name not in names]
    if missing:
        raise SystemExit("missing " + " ".join(missing))
    if any(name.startswith("META-INF/versions/9/") or name.endswith("module-info.class") for name in names):
        raise SystemExit("module-info was packaged")
    manifest = zf.read("META-INF/MANIFEST.MF").decode("utf-8")
    if "Multi-Release: true" not in manifest or "Automatic-Module-Name: codes.rafael.asmjdkbridge" not in manifest:
        raise SystemExit(manifest)
    base = zf.read("codes/rafael/asmjdkbridge/JdkClassReader.class")
    real = zf.read("META-INF/versions/24/codes/rafael/asmjdkbridge/JdkClassReader.class")
    if base[6] != 0 or base[7] != 52 or real[6] != 0 or real[7] != 68:
        raise SystemExit(f"class majors {base[6]}.{base[7]} {real[6]}.{real[7]}")
    if b"java/lang/classfile" in base or b"java/lang/UnsupportedOperationException" not in base:
        raise SystemExit("base reader is not the Java 8 stub")
    if b"java/lang/classfile/ClassFile" not in real:
        raise SystemExit("Java 24 reader lost ClassFile")
PY

%files -f .mfiles
%doc LICENSE
